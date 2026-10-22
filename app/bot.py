"""Telegram bot polling startup entrypoint."""

import asyncio

from aiogram import Bot, Dispatcher

from app.config.loader import load_settings
from app.db.repositories.sqlite import SQLiteCatalogRepository, SQLiteUserRepository
from app.db.sqlite import connect_sqlite, initialize_schema
from app.handlers.router import build_router
from app.services.catalog import CatalogService


def create_dispatcher() -> Dispatcher:
    """Create and configure the Telegram dispatcher."""

    settings = load_settings()
    connection = connect_sqlite(settings.sqlite)
    initialize_schema(connection)
    catalog_repository = SQLiteCatalogRepository(connection)
    catalog_repository.seed_game_catalog()
    if settings.payments.provider == "mock":
        connection.execute("update payment_methods set is_active = 0 where ticker != 'demo'")
        connection.execute(
            "insert or ignore into payment_methods "
            "(ticker, display_name, network, asset, destination_address, confirmations_required) "
            "values ('demo', 'Демо без оплаты', 'DEMO', 'DEMO', 'DEMO-NOT-A-WALLET', 1)"
        )
        connection.commit()
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_router(
            SQLiteUserRepository(connection),
            catalog=CatalogService(catalog_repository),
            main_banner_path=settings.bot.main_banner_path,
        )
    )
    return dispatcher


async def run_polling() -> None:
    """Run Telegram long polling."""

    settings = load_settings()
    bot = Bot(token=settings.bot.token)
    dispatcher = create_dispatcher()
    await dispatcher.start_polling(
        bot,
        polling_timeout=settings.bot.polling_timeout_seconds,
        allowed_updates=dispatcher.resolve_used_update_types(),
    )


def main() -> None:
    """Run the Telegram polling process."""

    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
