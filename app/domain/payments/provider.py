"""Payment provider protocol."""

from typing import Protocol

from app.domain.payments.entities import PaymentInvoice, PaymentMethod, ProviderPaymentEvent


class PaymentProvider(Protocol):
    """Provider interface used by application services."""

    async def create_invoice(
        self, method: PaymentMethod, order_id: int, amount_minor: int
    ) -> PaymentInvoice:
        """Create a provider invoice for an order."""

    async def poll_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        """Poll provider state for one invoice."""

    async def reconcile_invoice(self, invoice: PaymentInvoice) -> list[ProviderPaymentEvent]:
        """Perform a deeper provider reconciliation for one invoice."""
