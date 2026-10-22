"""Payment domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.data.enums import PaymentStatus


@dataclass(slots=True)
class PaymentMethod:
    """Configured CryptAPI payment method."""

    id: int | None
    ticker: str
    display_name: str
    network: str
    asset: str
    destination_address: str
    confirmations_required: int
    is_active: bool = True
    sort_order: int = 0
    icon_file_id: str | None = None


@dataclass(slots=True)
class PaymentInvoice:
    """Payment invoice persisted independently from provider field names."""

    id: int | None
    public_id: str
    order_id: int
    provider: str
    ticker: str
    network: str
    asset: str
    base_amount_minor: int
    base_currency: str
    expected_coin_amount: Decimal
    received_coin_amount: Decimal
    forwarded_coin_amount: Decimal | None
    exchange_rate: Decimal
    destination_address: str
    payment_address: str
    callback_url: str
    callback_nonce_hash: str
    provider_payload: dict[str, Any]
    minimum_transaction_coin: Decimal
    expires_at: datetime
    status: PaymentStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    confirmed_at: datetime | None = None
    last_polled_at: datetime | None = None
    next_poll_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProviderPaymentEvent:
    """Normalized payment event discovered by CryptAPI logs polling."""

    provider_uuid: str
    ticker: str
    address_in: str
    address_out: str
    txid_in: str
    txid_out: str | None
    pending: bool
    received_amount: Decimal
    forwarded_amount: Decimal | None
    confirmations: int
    raw_payload: dict[str, Any] = field(default_factory=dict)
