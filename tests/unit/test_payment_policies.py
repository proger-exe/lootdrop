"""Tests for payment amount rules."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.data.enums import PaymentStatus
from app.domain.payments.entities import PaymentInvoice
from app.domain.payments.policies import compare_received_amount, is_late_payment


def test_underpaid_when_received_below_tolerance() -> None:
    """Received amount below threshold is underpaid."""

    result = compare_received_amount(Decimal("10"), Decimal("9.9"), Decimal("0.01"))
    assert result.status == PaymentStatus.UNDERPAID
    assert result.missing_amount == Decimal("0.1")


def test_overpaid_when_received_exceeds_expected() -> None:
    """Received amount above expected is overpaid."""

    result = compare_received_amount(Decimal("10"), Decimal("10.2"), Decimal("0.01"))
    assert result.status == PaymentStatus.OVERPAID
    assert result.overpaid_amount == Decimal("0.2")


def test_confirmed_within_tolerance() -> None:
    """Small network rounding difference is accepted."""

    result = compare_received_amount(Decimal("10"), Decimal("9.995"), Decimal("0.01"))
    assert result.status == PaymentStatus.CONFIRMED


def test_late_payment_after_invoice_expiry() -> None:
    """Invoice is late after its expiry time."""

    invoice = PaymentInvoice(
        id=1,
        public_id="pay_test",
        order_id=1,
        provider="cryptapi",
        ticker="trc20/usdt",
        network="TRC-20",
        asset="USDT",
        base_amount_minor=1000,
        base_currency="USD",
        expected_coin_amount=Decimal("10"),
        received_coin_amount=Decimal("0"),
        forwarded_coin_amount=None,
        exchange_rate=Decimal("1"),
        destination_address="dest",
        payment_address="in",
        callback_url="https://example.test/callback",
        callback_nonce_hash="hash",
        provider_payload={},
        minimum_transaction_coin=Decimal("0"),
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        status=PaymentStatus.CREATED,
    )
    assert is_late_payment(invoice)
