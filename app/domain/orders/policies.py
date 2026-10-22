"""Order domain policies."""

from app.data.enums import OrderStatus
from app.data.statuses import ORDER_STATUS_TRANSITIONS


class InvalidOrderStatusTransition(ValueError):
    """Raised when an order transition is not allowed."""


def ensure_order_transition(current: OrderStatus, target: OrderStatus) -> None:
    """Validate an order status transition."""

    if target not in ORDER_STATUS_TRANSITIONS[current]:
        msg = f"Cannot transition order from {current} to {target}"
        raise InvalidOrderStatusTransition(msg)
