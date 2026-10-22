"""Environment settings loader."""

import os
from decimal import Decimal
from pathlib import Path

from app.config.models import (
    AppSettings,
    BotSettings,
    CryptAPISettings,
    MemorySettings,
    PaymentSettings,
    RaitoSettings,
    SQLiteSettings,
)
from app.data.enums import Environment


class ConfigurationError(RuntimeError):
    """Raised when required settings are missing or invalid."""


def _load_dotenv(path: str = ".env") -> None:
    """Load simple KEY=value pairs from a local dotenv file."""

    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


def _bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment value."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int_set(name: str) -> frozenset[int]:
    """Read comma-separated Telegram IDs."""

    value = os.getenv(name, "")
    if not value.strip():
        return frozenset()
    return frozenset(int(part.strip()) for part in value.split(",") if part.strip())


def _require(name: str) -> str:
    """Read a required environment variable."""

    value = os.getenv(name)
    if value is None or value == "":
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def load_settings() -> AppSettings:
    """Load settings from process environment."""

    _load_dotenv()
    payment_provider = os.getenv("PAYMENTS_PROVIDER", "mock")
    if payment_provider not in {"mock", "cryptapi"}:
        raise ConfigurationError("PAYMENTS_PROVIDER must be mock or cryptapi")
    environment = Environment(os.getenv("ENVIRONMENT", Environment.DEVELOPMENT))
    production_like = environment in {Environment.STAGING, Environment.PRODUCTION}
    bot_token = _require("BOT_TOKEN") if production_like else os.getenv("BOT_TOKEN", "")
    raito = RaitoSettings(
        devtools_enabled=_bool("RAITO_DEVTOOLS_ENABLED"),
        hot_reload_enabled=_bool("RAITO_HOT_RELOAD_ENABLED"),
        repl_enabled=_bool("RAITO_REPL_ENABLED"),
    )
    if production_like and (
        raito.devtools_enabled or raito.hot_reload_enabled or raito.repl_enabled
    ):
        raise ConfigurationError(
            "Raito devtools, hot reload, and REPL are forbidden outside development"
        )
    return AppSettings(
        app_name=os.getenv("APP_NAME", "LootDrop"),
        environment=environment,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        store_base_currency=os.getenv("STORE_BASE_CURRENCY", "RUB"),
        bot=BotSettings(
            token=bot_token,
            username=os.getenv("BOT_USERNAME", ""),
            owner_ids=_int_set("BOT_OWNER_IDS"),
            admin_ids=_int_set("BOT_ADMIN_IDS"),
            polling_timeout_seconds=int(os.getenv("TELEGRAM_POLLING_TIMEOUT_SECONDS", "30")),
            main_banner_path=os.getenv("BOT_MAIN_BANNER_PATH", ""),
        ),
        sqlite=SQLiteSettings(
            path=os.getenv("SQLITE_PATH", "./data/lootdrop.sqlite3"),
            busy_timeout_ms=int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000")),
            foreign_keys=_bool("SQLITE_FOREIGN_KEYS", True),
        ),
        memory=MemorySettings(
            lock_ttl_seconds=int(os.getenv("MEMORY_LOCK_TTL_SECONDS", "30")),
            rate_limit_ttl_seconds=int(os.getenv("MEMORY_RATE_LIMIT_TTL_SECONDS", "3600")),
        ),
        cryptapi=CryptAPISettings(
            base_url=os.getenv("CRYPTAPI_BASE_URL", "https://api.cryptapi.io"),
            callback_base_url=os.getenv("CRYPTAPI_CALLBACK_BASE_URL", ""),
            request_timeout=int(os.getenv("CRYPTAPI_REQUEST_TIMEOUT", "15")),
            default_confirmations=int(os.getenv("CRYPTAPI_DEFAULT_CONFIRMATIONS", "1")),
            public_key_cache_ttl=int(os.getenv("CRYPTAPI_PUBLIC_KEY_CACHE_TTL", "86400")),
        ),
        payments=PaymentSettings(
            provider=payment_provider,
            invoice_ttl_minutes=int(os.getenv("PAYMENT_INVOICE_TTL_MINUTES", "30")),
            check_cooldown_seconds=int(os.getenv("PAYMENT_CHECK_COOLDOWN_SECONDS", "20")),
            poll_interval_seconds=int(os.getenv("PAYMENT_POLL_INTERVAL_SECONDS", "20")),
            poll_batch_size=int(os.getenv("PAYMENT_POLL_BATCH_SIZE", "50")),
            tolerance_coin=Decimal(os.getenv("PAYMENT_TOLERANCE_COIN", "0.00000001")),
        ),
        raito=raito,
        fulfillment_encryption_key=os.getenv("FULFILLMENT_ENCRYPTION_KEY", ""),
        sentry_dsn=os.getenv("SENTRY_DSN") or None,
    )
