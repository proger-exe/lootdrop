"""Notification service backed by transactional outbox."""

from dataclasses import dataclass
from typing import Any

from app.db.repositories.protocols import OutboxRepository


@dataclass(slots=True)
class NotificationService:
    """Queues Telegram notifications outside database transactions."""

    outbox: OutboxRepository

    async def queue(self, event_type: str, payload: dict[str, Any]) -> None:
        """Queue a notification event."""

        await self.outbox.enqueue(event_type, payload)
