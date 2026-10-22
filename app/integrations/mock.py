"""Offline invoice previews; no wallet, network calls or settlement."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.data.enums import PaymentStatus
from app.domain.payments.entities import PaymentInvoice, PaymentMethod, ProviderPaymentEvent


@dataclass(slots=True)
class MockPaymentProvider:
    base_currency: str
    invoice_ttl_minutes: int

    async def create_invoice(
        self, method: PaymentMethod, order_id: int, amount_minor: int
    ) -> PaymentInvoice:
        if amount_minor <= 0:
            raise ValueError("Invoice amount must be positive")
        now = datetime.now(UTC)
        return PaymentInvoice(
            id=None,
            public_id=f"demo_{uuid4().hex}",
            order_id=order_id,
            provider="mock",
            ticker="demo",
            network="DEMO",
            asset="DEMO",
            base_amount_minor=amount_minor,
            base_currency=self.base_currency,
            expected_coin_amount=Decimal(amount_minor) / 100,
            received_coin_amount=Decimal(0),
            forwarded_coin_amount=None,
            exchange_rate=Decimal(1),
            destination_address="DEMO-NOT-A-WALLET",
            payment_address="DEMO-NOT-A-WALLET",
            callback_url="",
            callback_nonce_hash="",
            provider_payload={"demo": True},
            minimum_transaction_coin=Decimal(0),
            expires_at=now + timedelta(minutes=self.invoice_ttl_minutes),
            status=PaymentStatus.CREATED,
            created_at=now,
            updated_at=now,
        )

    async def poll_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        return []

    async def reconcile_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        return []
