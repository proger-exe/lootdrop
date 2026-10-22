"""Tests for CryptAPI log normalization."""

from decimal import Decimal

from app.integrations.cryptapi.dto import event_from_log


def test_event_from_log_normalizes_pending_flag() -> None:
    """CryptAPI pending field is normalized to bool."""

    event = event_from_log(
        {
            "uuid": "event-1",
            "txid_in": "tx-in",
            "address_in": "addr-in",
            "address_out": "addr-out",
            "pending": "1",
            "value_coin": "1.25",
            "confirmations": 0,
        },
        "trc20/usdt",
    )
    assert event.pending is True
    assert event.received_amount == Decimal("1.25")
