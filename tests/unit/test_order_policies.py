"""Tests for order status transitions."""

import pytest

from app.data.enums import OrderStatus
from app.domain.orders.policies import InvalidOrderStatusTransition, ensure_order_transition


def test_allows_documented_transition() -> None:
    """A documented transition is accepted."""

    ensure_order_transition(OrderStatus.AWAITING_PAYMENT, OrderStatus.PAID)


def test_rejects_undocumented_transition() -> None:
    """An undocumented transition is rejected."""

    with pytest.raises(InvalidOrderStatusTransition):
        ensure_order_transition(OrderStatus.DRAFT, OrderStatus.COMPLETED)
