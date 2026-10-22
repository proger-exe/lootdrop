"""User catalog handlers."""

from app.data.texts import TEXTS
from app.keyboards.factories import Button, button, rows
from app.services.catalog import CatalogService


async def render_categories(catalog: CatalogService) -> tuple[str, list[list[Button]]]:
    """Render category list."""

    categories = await catalog.list_categories()
    if not categories:
        return TEXTS["catalog.empty"], rows(button("← Главное меню", "menu:main"))
    keyboard = [
        [button(category.name, f"catalog:category:{category.id}", style="primary")]
        for category in categories
    ]
    keyboard.append([button("← Главное меню", "menu:main")])
    return TEXTS["catalog.categories"], keyboard


async def render_product(
    catalog: CatalogService, product_id: int
) -> tuple[str, list[list[Button]]]:
    """Render one product card."""

    product = await catalog.get_available_product(product_id)
    text = (
        f"💎 {product.name}\n\n"
        f"{product.short_description}\n\n"
        "────────────────\n\n"
        f"⏱ Обычно: до {product.fulfillment_sla_minutes} минут\n"
        f"💵 Цена: {product.price_minor / 100:.2f} {product.base_currency}\n\n"
        "Заказ выполняется менеджером после подтверждения оплаты."
    )
    return text, rows(
        button(
            f"✅ Купить за {product.price_minor / 100:.2f} {product.base_currency}",
            f"checkout:start:{product.id}",
            style="success",
        ),
        button("📋 Подробнее", f"catalog:details:{product.id}"),
        button("← Назад", f"catalog:category:{product.category_id}"),
    )
