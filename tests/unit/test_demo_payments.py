from decimal import Decimal

import pytest

from app.config.loader import ConfigurationError, load_settings
from app.data.enums import PaymentStatus
from app.domain.payments.entities import PaymentMethod
from app.handlers.user.payments import render_payment
from app.integrations.mock import MockPaymentProvider


@pytest.mark.asyncio
async def test_mock_never_exposes_a_wallet_or_confirms_payment():
    method = PaymentMethod(1, "btc", "Bitcoin", "BTC", "BTC", "real-wallet", 1)
    provider = MockPaymentProvider("RUB", 30)
    invoice = await provider.create_invoice(method, 1, 12345)
    assert invoice.expected_coin_amount == Decimal("123.45")
    assert invoice.status == PaymentStatus.CREATED
    assert invoice.payment_address == invoice.destination_address == "DEMO-NOT-A-WALLET"
    assert invoice.callback_url == ""
    assert await provider.poll_invoice(invoice) == []
    assert await provider.reconcile_invoice(invoice) == []
    text, _ = render_payment(invoice)
    assert "Оплата и выдача товара отключены" in text
    assert "real-wallet" not in text
    assert "Переведите" not in text
    with pytest.raises(ValueError):
        await provider.create_invoice(method, 1, 0)


def test_provider_defaults_to_mock_and_rejects_typo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PAYMENTS_PROVIDER", raising=False)
    assert load_settings().payments.provider == "mock"
    monkeypatch.setenv("PAYMENTS_PROVIDER", "moc")
    with pytest.raises(ConfigurationError):
        load_settings()


def test_dispatcher_bootstraps_demo_database(monkeypatch, tmp_path):
    from app.bot import create_dispatcher

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PAYMENTS_PROVIDER", "mock")
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "demo.sqlite3"))
    dispatcher = create_dispatcher()
    assert "callback_query" in dispatcher.resolve_used_update_types()
