"""Order application service."""

from dataclasses import dataclass

from app.data.enums import OrderStatus
from app.db.repositories.protocols import AuditLogRepository, OrderRepository, OutboxRepository
from app.domain.orders.entities import Order
from app.domain.orders.policies import ensure_order_transition


@dataclass(slots=True)
class OrderService:
    """Coordinates order state changes."""

    orders: OrderRepository
    outbox: OutboxRepository
    audit: AuditLogRepository

    async def transition(
        self, order: Order, target: OrderStatus, actor_type: str = "system"
    ) -> None:
        """Transition an order and emit history/audit side effects."""

        ensure_order_transition(order.status, target)
        changed = await self.orders.transition_status(order.id or 0, order.status, target)
        if not changed:
            return
        await self.audit.write(
            actor_type,
            "order_status_changed",
            "order",
            order.public_id,
            {"from": order.status.value, "to": target.value},
        )
        await self.outbox.enqueue(
            "order_status_changed",
            {"order_id": order.id, "public_id": order.public_id, "status": target.value},
        )

    async def queue_paid_order(self, order: Order) -> None:
        """Move a paid order into the manager queue."""

        await self.transition(order, OrderStatus.QUEUED)
        await self.outbox.enqueue(
            "order_queued", {"order_id": order.id, "public_id": order.public_id}
        )

    async def claim(self, order_id: int, manager_id: int) -> bool:
        """Claim an order atomically for a manager."""

        claimed = await self.orders.claim_order(order_id, manager_id)
        if claimed:
            await self.audit.write(
                "manager",
                "order_claimed",
                "order",
                str(order_id),
                {"manager_id": manager_id},
            )
            await self.outbox.enqueue(
                "order_claimed",
                {"order_id": order_id, "manager_id": manager_id},
            )
        return claimed
