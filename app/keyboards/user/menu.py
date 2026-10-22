"""User menu keyboards."""

from app.keyboards.factories import Button, button, rows


def legal_keyboard() -> list[list[Button]]:
    """Legal acceptance keyboard."""

    return rows(
        button("📄 Пользовательское соглашение", "legal:terms"),
        button("🔐 Политика конфиденциальности", "legal:privacy"),
        button("💸 Правила оплаты и возврата", "legal:refunds"),
        button("✅ Принимаю условия", "legal:accept", style="success"),
    )


def main_menu_keyboard() -> list[list[Button]]:
    """Main menu keyboard."""

    return rows(
        button("🎮 Игры", "catalog:open", style="primary"),
        button("📦 Мои заказы", "orders:mine"),
        [button("👤 Профиль", "profile:open"), button("💬 Поддержка", "support:open")],
        button("ℹ️ О сервисе", "about:open"),
    )


def checkout_start_keyboard(product_id: int) -> list[list[Button]]:
    """Checkout start keyboard."""

    return rows(
        button("Продолжить", f"checkout:continue:{product_id}", style="primary"),
        button("Отменить оформление", "checkout:cancel", style="danger"),
    )
