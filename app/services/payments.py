"""Payment application service using provider polling."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from app.data.enums import OrderStatus, PaymentStatus
from app.db.repositories.protocols import (
    AuditLogRepository,
    OrderRepository,
    OutboxRepository,
    PaymentRepository,
)
from app.domain.payments.entities import PaymentInvoice, ProviderPaymentEvent
from app.domain.payments.policies import compare_received_amount, is_late_payment
from app.domain.payments.provider import PaymentProvider


@dataclass(slots=True)
class PollResult:
    """Summary of a polling pass."""

    invoice_public_id: str
    processed_events: int
    duplicate_events: int
    final_status: PaymentStatus


@dataclass(slots=True)
class PaymentService:
    """Coordinates invoice creation and polling-based reconciliation."""

    payments: PaymentRepository
    orders: OrderRepository
    outbox: OutboxRepository
    audit: AuditLogRepository
    provider: PaymentProvider
    tolerance_coin: Decimal

    async def create_invoice(
        self,
        method_id: int,
        order_id: int,
        amount_minor: int,
    ) -> PaymentInvoice:
        """Create and store a provider invoice."""

        method = await self.payments.get_method(method_id)
        if method is None or not method.is_active:
            raise ValueError("Payment method is unavailable")
        invoice = await self.provider.create_invoice(method, order_id, amount_minor)
        saved = await self.payments.save_invoice(invoice)
        await self.audit.write(
            "user",
            "invoice_created",
            "payment_invoice",
            saved.public_id,
            {"order_id": order_id, "ticker": method.ticker},
        )
        return saved

    async def poll_due_invoices(self, limit: int) -> list[PollResult]:
        """Poll all invoices currently due for reconciliation."""

        invoices = await self.payments.list_active_for_polling(limit)
        return [await self.poll_invoice(invoice) for invoice in invoices]

    async def poll_invoice(self, invoice: PaymentInvoice) -> PollResult:
        """Poll one invoice and apply discovered payment events."""

        events = await self.provider.poll_invoice(invoice)
        processed = 0
        duplicates = 0
        for event in events:
            if not await self.payments.record_poll_event(invoice, event):
                duplicates += 1
                continue
            processed += 1
            await self._apply_event(invoice, event)
        refreshed = await self.payments.get_invoice(invoice.id or 0)
        final_status = refreshed.status if refreshed is not None else invoice.status
        return PollResult(invoice.public_id, processed, duplicates, final_status)

    async def _apply_event(self, invoice: PaymentInvoice, event: ProviderPaymentEvent) -> None:
        """Apply one normalized provider event to invoice and order state."""

        self._validate_event_matches_invoice(invoice, event)
        if event.pending:
            await self.payments.update_invoice_status(
                invoice.id or 0,
                PaymentStatus.PENDING,
                event.received_amount,
            )
            await self.outbox.enqueue(
                "payment_pending",
                {"invoice_id": invoice.id, "order_id": invoice.order_id},
            )
            return
        amount_check = compare_received_amount(
            invoice.expected_coin_amount,
            event.received_amount,
            self.tolerance_coin,
        )
        status = amount_check.status
        if status in {PaymentStatus.CONFIRMED, PaymentStatus.OVERPAID} and is_late_payment(invoice):
            status = PaymentStatus.LATE_PAYMENT
        await self.payments.update_invoice_status(
            invoice.id or 0,
            status,
            event.received_amount,
        )
        await self.audit.write(
            "system",
            f"payment_{status.value.lower()}",
            "payment_invoice",
            invoice.public_id,
            {"received": str(event.received_amount), "txid_in": event.txid_in},
        )
        if status in {PaymentStatus.CONFIRMED, PaymentStatus.OVERPAID}:
            order = await self.orders.get_order(invoice.order_id)
            if order is not None and order.status == OrderStatus.AWAITING_PAYMENT:
                paid = await self.orders.transition_status(
                    invoice.order_id,
                    OrderStatus.AWAITING_PAYMENT,
                    OrderStatus.PAID,
                )
                if paid:
                    order.status = OrderStatus.PAID
                    await self.orders.transition_status(
                        invoice.order_id,
                        OrderStatus.PAID,
                        OrderStatus.QUEUED,
                    )
                    await self.outbox.enqueue(
                        "payment_confirmed",
                        {"invoice_id": invoice.id, "order_id": invoice.order_id},
                    )
                    await self.outbox.enqueue(
                        "order_queued",
                        {"order_id": invoice.order_id},
                    )
        elif status == PaymentStatus.UNDERPAID:
            await self.outbox.enqueue(
                "payment_underpaid",
                {
                    "invoice_id": invoice.id,
                    "order_id": invoice.order_id,
                    "received": str(event.received_amount),
                    "at": datetime.now(UTC).isoformat(),
                },
            )
        elif status == PaymentStatus.LATE_PAYMENT:
            await self.outbox.enqueue(
                "payment_late",
                {"invoice_id": invoice.id, "order_id": invoice.order_id},
            )

    @staticmethod
    def _validate_event_matches_invoice(
        invoice: PaymentInvoice,
        event: ProviderPaymentEvent,
    ) -> None:
        """Ensure provider event belongs to the expected invoice."""

        if event.ticker != invoice.ticker:
            raise ValueError("Provider event ticker mismatch")
        if event.address_in != invoice.payment_address:
            raise ValueError("Provider event address_in mismatch")
        if event.address_out != invoice.destination_address:
            raise ValueError("Provider event address_out mismatch")
