"""User payment screen rendering."""

from app.domain.payments.entities import PaymentInvoice
from app.keyboards.factories import Button, button, rows


def render_payment(invoice: PaymentInvoice) -> tuple[str, list[list[Button]]]:
    """Render payment instructions for an invoice."""

    if invoice.provider == "mock":
        return (
            f"Демо-заказ {invoice.public_id}\n\n"
            f"Сумма: {invoice.base_amount_minor / 100:.2f} {invoice.base_currency}\n"
            "Это демонстрация оформления заказа. Оплата и выдача товара отключены.",
            rows(button("Мои заказы", "orders:mine"), button("Главное меню", "menu:main")),
        )

    text = (
        f"💳 Оплата заказа {invoice.public_id}\n\n"
        "Переведите точную сумму на указанный адрес.\n\n"
        "────────────────\n\n"
        f"🪙 Валюта: {invoice.asset}\n"
        f"🌐 Сеть: {invoice.network}\n"
        f"💰 Сумма: {invoice.expected_coin_amount} {invoice.asset}\n\n"
        f"📍 Адрес:\n{invoice.payment_address}\n\n"
        f"⏳ Счёт действует до:\n{invoice.expires_at:%d.%m.%Y %H:%M}\n\n"
        f"Отправляйте только {invoice.asset} через сеть {invoice.network}."
    )
    return text, rows(
        button("Проверить оплату", f"payment:poll:{invoice.id}", style="primary"),
        button("Выбрать другую валюту", f"payment:methods:{invoice.order_id}"),
        button("Отменить неоплаченный заказ", f"order:cancel:{invoice.order_id}", style="danger"),
    )
