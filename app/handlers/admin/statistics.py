"""Admin statistics screen."""


def render_admin_home(stats: dict[str, int]) -> str:
    """Render compact admin dashboard."""

    return (
        "⚙️ LootDrop Admin\n\n"
        "Сегодня:\n"
        f"Заказов: {stats.get('orders', 0)}\n"
        f"Оплачено: {stats.get('paid', 0)}\n"
        f"Выполнено: {stats.get('completed', 0)}\n"
        f"В очереди: {stats.get('queued', 0)}\n"
        f"Проблемных: {stats.get('problematic', 0)}"
    )
