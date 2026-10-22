"""Payment amount and expiry policies."""

from datetime import UTC, datetime
from decimal import Decimal

from app.data.enums import PaymentStatus
from app.domain.orders.entities import PaymentAmountCheck
from app.domain.payments.entities import PaymentInvoice


def compare_received_amount(
    expected: Decimal,
    received: Decimal,
    tolerance: Decimal,
) -> PaymentAmountCheck:
    """Compare received crypto amount in the invoice currency."""

    threshold = expected - tolerance
    if received < threshold:
        return PaymentAmountCheck(
            status=PaymentStatus.UNDERPAID,
            missing_amount=expected - received,
            overpaid_amount=Decimal("0"),
        )
    if received > expected:
        return PaymentAmountCheck(
            status=PaymentStatus.OVERPAID,
            missing_amount=Decimal("0"),
            overpaid_amount=received - expected,
        )
    return PaymentAmountCheck(
        status=PaymentStatus.CONFIRMED,
        missing_amount=Decimal("0"),
        overpaid_amount=Decimal("0"),
    )


def is_late_payment(invoice: PaymentInvoice, now: datetime | None = None) -> bool:
    """Return whether an invoice payment arrived after the application TTL."""

    current = now or datetime.now(UTC)
    return current > invoice.expires_at
