"""Manager queue handlers."""

from app.services.orders import OrderService


async def claim_order(order_service: OrderService, order_id: int, manager_id: int) -> str:
    """Claim an order for a manager."""

    if await order_service.claim(order_id, manager_id):
        return "✅ Заказ взят в работу."
    return "Этот заказ уже взял другой менеджер."
