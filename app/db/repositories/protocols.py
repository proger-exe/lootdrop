"""Repository protocols used by services."""

from typing import Any, Protocol

from app.data.enums import OrderStatus, PaymentStatus, StaffRole
from app.domain.catalog.entities import Category, Product
from app.domain.orders.entities import Order
from app.domain.payments.entities import PaymentInvoice, PaymentMethod, ProviderPaymentEvent


class UserRepository(Protocol):
    """User persistence interface."""

    async def upsert_telegram_user(self, telegram_user: dict[str, Any]) -> int:
        """Create or update a Telegram user and return internal user ID."""

    async def has_accepted_legal(self, user_id: int, version: str) -> bool:
        """Return whether a user accepted the current legal version."""

    async def accept_legal(self, user_id: int, version: str, language_code: str | None) -> None:
        """Persist legal acceptance."""


class StaffRepository(Protocol):
    """Staff persistence interface."""

    async def get_roles(self, telegram_id: int) -> set[StaffRole]:
        """Return staff roles for a Telegram account."""


class CatalogRepository(Protocol):
    """Catalog persistence interface."""

    async def list_categories(self, *, active_only: bool = True) -> list[Category]:
        """List categories."""

    async def list_products(self, category_id: int, *, active_only: bool = True) -> list[Product]:
        """List products in a category."""

    async def get_product(self, product_id: int) -> Product | None:
        """Get one product."""

    async def get_category(self, category_id: int) -> Category | None:
        """Get one category."""


class OrderRepository(Protocol):
    """Order persistence interface."""

    async def create_order(self, order: Order) -> Order:
        """Create an order idempotently."""

    async def get_order(self, order_id: int) -> Order | None:
        """Get one order."""

    async def get_by_public_id(self, public_id: str) -> Order | None:
        """Get one order by public ID."""

    async def transition_status(
        self,
        order_id: int,
        from_status: OrderStatus,
        to_status: OrderStatus,
    ) -> bool:
        """Transition status if current status matches."""

    async def claim_order(self, order_id: int, manager_id: int) -> bool:
        """Atomically claim a queued order."""

    async def list_user_orders(self, user_id: int, statuses: set[OrderStatus]) -> list[Order]:
        """List orders belonging to a user."""


class PaymentRepository(Protocol):
    """Payment persistence interface."""

    async def list_active_for_polling(self, limit: int) -> list[PaymentInvoice]:
        """List invoices eligible for polling."""

    async def get_invoice(self, invoice_id: int) -> PaymentInvoice | None:
        """Get one invoice."""

    async def get_method(self, method_id: int) -> PaymentMethod | None:
        """Get one payment method."""

    async def save_invoice(self, invoice: PaymentInvoice) -> PaymentInvoice:
        """Persist a new invoice."""

    async def record_poll_event(
        self,
        invoice: PaymentInvoice,
        event: ProviderPaymentEvent,
    ) -> bool:
        """Persist a polled provider event; return false for duplicates."""

    async def update_invoice_status(
        self,
        invoice_id: int,
        status: PaymentStatus,
        received_amount: object,
    ) -> None:
        """Update invoice payment state."""


class OutboxRepository(Protocol):
    """Transactional outbox persistence interface."""

    async def enqueue(self, event_type: str, payload: dict[str, Any]) -> None:
        """Enqueue a reliable notification/event."""


class AuditLogRepository(Protocol):
    """Audit persistence interface."""

    async def write(
        self,
        actor_type: str,
        action: str,
        entity_type: str,
        entity_id: str,
        data: dict[str, Any],
    ) -> None:
        """Write an append-only audit event."""
