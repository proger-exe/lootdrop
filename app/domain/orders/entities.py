"""Order domain entities."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.data.enums import OrderStatus, PaymentStatus


@dataclass(slots=True)
class OrderItem:
    """Snapshot of a purchased product inside an order."""

    product_id: int
    product_snapshot: dict[str, Any]
    quantity: int
    unit_price_minor: int
    total_price_minor: int


@dataclass(slots=True)
class Order:
    """Order aggregate."""

    id: int | None
    public_id: str
    user_id: int
    status: OrderStatus
    base_amount_minor: int
    base_currency: str
    checkout_idempotency_key: str
    items: list[OrderItem] = field(default_factory=list)
    assigned_manager_id: int | None = None
    fulfillment_data: dict[str, Any] = field(default_factory=dict)
    payment_status: PaymentStatus | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PaymentAmountCheck:
    """Result of comparing expected and received crypto amounts."""

    status: PaymentStatus
    missing_amount: Decimal
    overpaid_amount: Decimal
