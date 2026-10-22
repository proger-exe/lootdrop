"""Background job for payment polling."""

from dataclasses import dataclass

from app.services.payments import PaymentService, PollResult


@dataclass(slots=True)
class PaymentPollingJob:
    """Poll due invoices through PaymentService."""

    payments: PaymentService
    batch_size: int

    async def run_once(self) -> list[PollResult]:
        """Run one polling pass."""

        return await self.payments.poll_due_invoices(self.batch_size)
