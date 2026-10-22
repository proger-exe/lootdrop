"""Catalog domain entities."""

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Category:
    """Product category."""

    id: int | None
    slug: str
    name: str
    description: str
    is_active: bool
    sort_order: int
    media_file_id: str | None = None


@dataclass(slots=True)
class Product:
    """Digital product sold through the bot."""

    id: int | None
    category_id: int
    sku: str
    name: str
    short_description: str
    full_description: str
    price_minor: int
    base_currency: str
    fulfillment_sla_minutes: int
    fulfillment_schema: dict[str, Any]
    is_active: bool
    is_featured: bool = False
    sort_order: int = 0
    media_file_id: str | None = None
