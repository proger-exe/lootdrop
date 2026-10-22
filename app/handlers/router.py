"""Aiogram router wiring."""

import asyncio
import json
import secrets
from pathlib import Path
from sqlite3 import Row
from urllib.parse import urlparse

import aiohttp
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.config.loader import load_settings
from app.data.enums import OrderStatus
from app.data.texts import LEGAL_VERSION, TEXTS
from app.db.repositories.sqlite import SQLiteUserRepository
from app.domain.catalog.entities import Product
from app.domain.payments.entities import PaymentInvoice, PaymentMethod
from app.handlers.user.catalog import render_categories, render_product
from app.handlers.user.payments import render_payment
from app.handlers.user.start import accept_legal, render_start
from app.integrations.cryptapi.client import CryptAPIClient
from app.integrations.cryptapi.provider import CryptAPIPaymentProvider
from app.integrations.mock import MockPaymentProvider
from app.keyboards.factories import Button, as_aiogram_markup, button, open_menu_reply_keyboard
from app.keyboards.user.menu import checkout_start_keyboard, legal_keyboard, main_menu_keyboard
from app.services.catalog import CatalogService


def _payment_method_buttons(rows_: list[Row], product_id: int) -> list[list[Button]]:
    """Build active payment method buttons."""

    keyboard = [
        [
            button(
                f"{row['asset']} · {row['network']}",
                f"payment:method:{product_id}:{row['id']}",
                style="primary",
            )
        ]
        for row in rows_
    ]
    keyboard.append([button("← Назад к товару", f"catalog:product:{product_id}")])
    return keyboard


def _is_remote_image_path(path: str) -> bool:
    """Return whether a banner path is a Telegram-fetchable URL."""

    parsed = urlparse(path)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _payment_method_from_row(row: Row) -> PaymentMethod:
    """Build a payment method entity from SQLite."""

    return PaymentMethod(
        id=int(row["id"]),
        ticker=str(row["ticker"]),
        display_name=str(row["display_name"]),
        network=str(row["network"]),
        asset=str(row["asset"]),
        destination_address=str(row["destination_address"]),
        confirmations_required=int(row["confirmations_required"]),
        is_active=bool(row["is_active"]),
        sort_order=int(row["sort_order"]),
        icon_file_id=row["icon_file_id"],
    )


def _create_order(connection: object, user_id: int, product: Product) -> int:
    """Create an awaiting-payment order for one product."""

    public_id = f"ord_{secrets.token_urlsafe(8)}"
    idempotency_key = f"checkout_{user_id}_{product.id}_{secrets.token_urlsafe(12)}"
    cursor = connection.execute(
        """
        insert into orders (
            public_id, user_id, status, base_amount_minor, base_currency,
            checkout_idempotency_key
        )
        values (?, ?, ?, ?, ?, ?)
        """,
        (
            public_id,
            user_id,
            OrderStatus.AWAITING_PAYMENT,
            product.price_minor,
            product.base_currency,
            idempotency_key,
        ),
    )
    order_id = int(cursor.lastrowid)
    connection.execute(
        """
        insert into order_items (
            order_id, product_id, product_snapshot, quantity, unit_price_minor, total_price_minor
        )
        values (?, ?, ?, 1, ?, ?)
        """,
        (
            order_id,
            product.id,
            json.dumps(
                {
                    "sku": product.sku,
                    "name": product.name,
                    "short_description": product.short_description,
                    "base_currency": product.base_currency,
                },
                ensure_ascii=False,
            ),
            product.price_minor,
            product.price_minor,
        ),
    )
    connection.commit()
    return order_id


def _save_invoice(connection: object, invoice: PaymentInvoice) -> PaymentInvoice:
    """Persist a CryptAPI invoice and return it with an id."""

    cursor = connection.execute(
        """
        insert into payment_invoices (
            public_id, order_id, provider, ticker, network, asset, base_amount_minor,
            base_currency, expected_coin_amount, received_coin_amount, forwarded_coin_amount,
            exchange_rate, destination_address, payment_address, callback_url,
            callback_nonce_hash, provider_payload, minimum_transaction_coin, expires_at,
            status, next_poll_at
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice.public_id,
            invoice.order_id,
            invoice.provider,
            invoice.ticker,
            invoice.network,
            invoice.asset,
            invoice.base_amount_minor,
            invoice.base_currency,
            str(invoice.expected_coin_amount),
            str(invoice.received_coin_amount),
            (
                str(invoice.forwarded_coin_amount)
                if invoice.forwarded_coin_amount is not None
                else None
            ),
            str(invoice.exchange_rate),
            invoice.destination_address,
            invoice.payment_address,
            invoice.callback_url,
            invoice.callback_nonce_hash,
            json.dumps(invoice.provider_payload),
            str(invoice.minimum_transaction_coin),
            invoice.expires_at.isoformat(),
            invoice.status,
            invoice.next_poll_at.isoformat() if invoice.next_poll_at is not None else None,
        ),
    )
    connection.commit()
    invoice.id = int(cursor.lastrowid)
    return invoice


def build_router(
    users: SQLiteUserRepository,
    catalog: CatalogService,
    main_banner_path: str,
) -> Router:
    """Build the application router."""

    router = Router(name="lootdrop")

    @router.message(CommandStart())
    async def start(message: Message) -> None:
        """Handle /start."""

        if message.from_user is None:
            return
        user_id = await users.upsert_telegram_user(message.from_user.model_dump())
        has_legal = await users.has_accepted_legal(user_id, LEGAL_VERSION)
        text, keyboard = await render_start(user_id, has_legal)
        await message.answer(
            "Нажмите «Открыть меню», чтобы открыть магазин.",
            reply_markup=open_menu_reply_keyboard(),
        )
        await answer_screen(message, text, keyboard, main_banner_path, with_banner=has_legal)

    @router.message(F.text.casefold() == "открыть меню")
    async def open_menu(message: Message) -> None:
        """Open menu from reply keyboard."""

        if message.from_user is None:
            return
        user_id = await users.upsert_telegram_user(message.from_user.model_dump())
        has_legal = await users.has_accepted_legal(user_id, LEGAL_VERSION)
        text, keyboard = await render_start(user_id, has_legal)
        await answer_screen(message, text, keyboard, main_banner_path, with_banner=has_legal)

    @router.callback_query(F.data == "legal:accept")
    async def legal_accept(callback: CallbackQuery) -> None:
        """Accept legal terms."""

        if callback.from_user is None or callback.message is None:
            return
        user_id = await users.upsert_telegram_user(callback.from_user.model_dump())
        text, keyboard = await accept_legal(
            users,
            user_id,
            callback.from_user.language_code,
        )
        await edit_callback_message(callback, text, keyboard, main_banner_path, with_banner=True)
        await callback.answer("Условия приняты")

    @router.callback_query(F.data.in_({"legal:terms", "legal:privacy", "legal:refunds"}))
    async def legal_document(callback: CallbackQuery) -> None:
        """Render starter legal document text."""

        if callback.message is None:
            return
        title_by_key = {
            "legal:terms": "📄 Пользовательское соглашение",
            "legal:privacy": "🔐 Политика конфиденциальности",
            "legal:refunds": "💸 Правила оплаты и возврата",
        }
        text = (
            f"{title_by_key[str(callback.data)]}\n\n"
            "Версия: 1.0\n\n"
            "Заказы выполняются вручную после подтверждения оплаты. "
            "Срок исполнения ориентировочный. Указывайте корректные данные аккаунта. "
            "Не отправляйте пароли, 2FA-коды и лишние персональные данные."
        )
        await edit_callback_message(callback, text, legal_keyboard(), main_banner_path)
        await callback.answer()

    @router.callback_query(F.data == "menu:main")
    async def main_menu(callback: CallbackQuery) -> None:
        """Render main menu."""

        await edit_callback_message(
            callback,
            TEXTS["menu.main"],
            main_menu_keyboard(),
            main_banner_path,
            with_banner=True,
        )
        await callback.answer()

    @router.callback_query(F.data == "catalog:open")
    async def catalog_open(callback: CallbackQuery) -> None:
        """Render categories."""

        text, keyboard = await render_categories(catalog)
        await edit_callback_message(callback, text, keyboard, main_banner_path)
        await callback.answer()

    @router.callback_query(F.data.startswith("catalog:category:"))
    async def category_open(callback: CallbackQuery) -> None:
        """Render products in a category."""

        if callback.data is None:
            return
        category_id = int(callback.data.rsplit(":", 1)[1])
        category = await catalog.get_category(category_id)
        products = await catalog.list_products(category_id)
        keyboard = [
            [
                button(
                    f"{product.name} · {product.price_minor / 100:.2f} {product.base_currency}",
                    f"catalog:product:{product.id}",
                    style="primary",
                )
            ]
            for product in products
        ]
        keyboard.append([button("← Каталог", "catalog:open")])
        await edit_callback_message(
            callback,
            f"{category.name}\n\n{category.description}\n\nДоступные товары:",
            keyboard,
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("catalog:product:"))
    async def product_open(callback: CallbackQuery) -> None:
        """Render a product card."""

        if callback.data is None:
            return
        product_id = int(callback.data.rsplit(":", 1)[1])
        text, keyboard = await render_product(catalog, product_id)
        await edit_callback_message(callback, text, keyboard, main_banner_path)
        await callback.answer()

    @router.callback_query(F.data.startswith("checkout:start:"))
    async def checkout_start(callback: CallbackQuery) -> None:
        """Render checkout start screen."""

        if callback.data is None:
            return
        product_id = int(callback.data.rsplit(":", 1)[1])
        await edit_callback_message(
            callback,
            TEXTS["checkout.start"],
            checkout_start_keyboard(product_id),
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("checkout:continue:"))
    async def checkout_continue(callback: CallbackQuery) -> None:
        """Render payment method selection for checkout."""

        if callback.data is None:
            return
        product_id = int(callback.data.rsplit(":", 1)[1])
        product = await catalog.get_available_product(product_id)
        payment_methods = users.connection.execute(
            """
            select id, asset, network
            from payment_methods
            where is_active = 1
            order by sort_order, id
            """
        ).fetchall()
        if not payment_methods:
            await edit_callback_message(
                callback,
                "🪙 Оплата\n\nСейчас нет доступных способов оплаты.",
                [[button("← Назад к товару", f"catalog:product:{product_id}")]],
                main_banner_path,
            )
            await callback.answer()
            return
        await edit_callback_message(
            callback,
            (
                f"{TEXTS['payment.choose']}\n\n"
                f"Товар: {product.name}\n"
                f"Сумма: {product.price_minor / 100:.2f} {product.base_currency}"
            ),
            _payment_method_buttons(payment_methods, product_id),
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("payment:method:"))
    async def payment_method(callback: CallbackQuery) -> None:
        """Create a CryptAPI invoice for the selected payment method."""

        if callback.data is None or callback.from_user is None:
            return
        _, _, product_id_raw, method_id_raw = callback.data.split(":", 3)
        product_id = int(product_id_raw)
        method_id = int(method_id_raw)
        await callback.answer("Создаю адрес оплаты...")
        user_id = await users.upsert_telegram_user(callback.from_user.model_dump())
        product = await catalog.get_available_product(product_id)
        method_row = users.connection.execute(
            """
            select id, ticker, display_name, network, asset, destination_address,
                   confirmations_required, is_active, sort_order, icon_file_id
            from payment_methods
            where id = ? and is_active = 1
            """,
            (method_id,),
        ).fetchone()
        if method_row is None:
            await edit_callback_message(
                callback,
                "🪙 Оплата\n\nЭтот способ оплаты сейчас недоступен.",
                [[button("← Назад", f"checkout:continue:{product_id}")]],
                main_banner_path,
            )
            return
        settings = load_settings()
        order_id = _create_order(users.connection, user_id, product)
        method = _payment_method_from_row(method_row)
        try:
            if settings.payments.provider == "mock":
                invoice = await MockPaymentProvider(
                    settings.store_base_currency, settings.payments.invoice_ttl_minutes
                ).create_invoice(method, order_id, product.price_minor)
            else:
                async with aiohttp.ClientSession() as session:
                    provider = CryptAPIPaymentProvider(
                        client=CryptAPIClient(
                            settings.cryptapi.base_url,
                            session,
                            settings.cryptapi.request_timeout,
                        ),
                        cryptapi_settings=settings.cryptapi,
                        payment_settings=settings.payments,
                        base_currency=settings.store_base_currency,
                    )
                    invoice = await provider.create_invoice(method, order_id, product.price_minor)
        except Exception:
            await edit_callback_message(
                callback,
                "Не удалось создать счёт. Попробуйте позже.",
                [[button("← Назад", f"checkout:continue:{product_id}")]],
                main_banner_path,
            )
            return
        invoice = _save_invoice(users.connection, invoice)
        text, keyboard = render_payment(invoice)
        await edit_callback_message(callback, text, keyboard, main_banner_path)

    @router.callback_query(F.data == "orders:mine")
    async def orders_mine(callback: CallbackQuery) -> None:
        """Render order history."""

        cards = await users.list_order_cards(callback.from_user.id)
        if not cards:
            await edit_callback_message(
                callback,
                TEXTS["orders.empty"],
                [
                    [button("🎮 Открыть игры", "catalog:open", style="primary")],
                    [button("← Главное меню", "menu:main")],
                ],
                main_banner_path,
            )
            await callback.answer()
            return
        await edit_callback_message(
            callback,
            "📦 Мои заказы\n\n" + "\n\n".join(cards),
            [[button("🎮 Открыть игры", "catalog:open")], [button("← Главное меню", "menu:main")]],
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data == "profile:open")
    async def profile_open(callback: CallbackQuery) -> None:
        """Render profile."""

        profile = await users.profile_summary(callback.from_user.id)
        username = profile.get("username") or "не указан"
        first_name = profile.get("first_name") or "игрок"
        text = (
            f"👤 Профиль\n\nИмя: {first_name}\nUsername: @{username}"
            if username != "не указан"
            else f"Username: {username}"
        )
        text = (
            f"{text}\n"
            f"Заказов всего: {profile.get('orders_total', 0)}\n"
            f"Активных заказов: {profile.get('active_orders', 0)}\n\n"
            "Данные аккаунтов вводятся только внутри конкретного заказа."
        )
        await edit_callback_message(
            callback,
            text,
            [
                [button("📦 История заказов", "orders:mine")],
                [button("← Главное меню", "menu:main")],
            ],
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data == "support:open")
    async def support_open(callback: CallbackQuery) -> None:
        """Render support entry."""

        await edit_callback_message(
            callback,
            TEXTS["support.main"],
            [
                [button("Проблема с оплатой", "support:create:payment")],
                [button("Проблема с заказом", "support:create:order")],
                [button("Вопрос по товару", "support:create:product")],
                [button("← Главное меню", "menu:main")],
            ],
            main_banner_path,
        )
        await callback.answer()

    @router.callback_query(F.data == "about:open")
    async def about_open(callback: CallbackQuery) -> None:
        """Render about screen."""

        await edit_callback_message(
            callback,
            TEXTS["about.main"],
            [[button("← Главное меню", "menu:main")]],
            main_banner_path,
        )
        await callback.answer()

    return router


async def edit_callback_message(
    callback: CallbackQuery,
    text: str,
    keyboard: list[list[Button]],
    main_banner_path: str,
    *,
    with_banner: bool = False,
) -> None:
    """Edit a callback message when Telegram still exposes it as editable."""

    message = callback.message
    if not isinstance(message, Message):
        if callback.bot is None:
            return
        await send_screen(
            callback.bot,
            callback.from_user.id,
            text,
            keyboard,
            main_banner_path,
            with_banner=with_banner,
        )
        return
    if message.photo:
        await message.edit_caption(caption=text, reply_markup=as_aiogram_markup(keyboard))
        return
    if with_banner:
        if message.bot is None:
            return
        await message.delete()
        await send_screen(
            message.bot,
            message.chat.id,
            text,
            keyboard,
            main_banner_path,
            with_banner=True,
        )
        return
    await message.edit_text(text, reply_markup=as_aiogram_markup(keyboard))


async def answer_screen(
    message: Message,
    text: str,
    keyboard: list[list[Button]],
    main_banner_path: str,
    *,
    with_banner: bool,
) -> None:
    """Answer a user with either a photo-caption screen or text screen."""

    if message.bot is None:
        return
    await send_screen(
        message.bot,
        message.chat.id,
        text,
        keyboard,
        main_banner_path,
        with_banner=with_banner,
    )


async def send_screen(
    bot: Bot,
    chat_id: int,
    text: str,
    keyboard: list[list[Button]],
    main_banner_path: str,
    *,
    with_banner: bool,
) -> None:
    """Send a screen with optional main banner."""

    if with_banner and _is_remote_image_path(main_banner_path):
        await bot.send_photo(
            chat_id,
            main_banner_path,
            caption=text,
            reply_markup=as_aiogram_markup(keyboard),
        )
        return
    if with_banner and main_banner_path and await asyncio.to_thread(Path(main_banner_path).is_file):
        await bot.send_photo(
            chat_id,
            FSInputFile(main_banner_path),
            caption=text,
            reply_markup=as_aiogram_markup(keyboard),
        )
        return
    await bot.send_message(chat_id, text, reply_markup=as_aiogram_markup(keyboard))
