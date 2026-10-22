"""Catalog application service."""

from dataclasses import dataclass

from app.db.repositories.protocols import CatalogRepository
from app.domain.catalog.entities import Category, Product


@dataclass(slots=True)
class CatalogService:
    """Reads active catalog data for Telegram screens."""

    repository: CatalogRepository

    async def list_categories(self) -> list[Category]:
        """List active categories."""

        return await self.repository.list_categories(active_only=True)

    async def list_products(self, category_id: int) -> list[Product]:
        """List active products in a category."""

        return await self.repository.list_products(category_id, active_only=True)

    async def get_category(self, category_id: int) -> Category:
        """Return an active category."""

        category = await self.repository.get_category(category_id)
        if category is None or not category.is_active:
            raise ValueError("Category is unavailable")
        return category

    async def get_available_product(self, product_id: int) -> Product:
        """Return an active product or raise a user-safe error."""

        product = await self.repository.get_product(product_id)
        if product is None or not product.is_active:
            raise ValueError("Product is unavailable")
        return product
