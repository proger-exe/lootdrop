"""Application settings models."""

from dataclasses import dataclass
from decimal import Decimal

from app.data.enums import Environment


@dataclass(frozen=True, slots=True)
class BotSettings:
    """Telegram bot settings."""

    token: str
    username: str
    owner_ids: frozenset[int]
    admin_ids: frozenset[int]
    polling_timeout_seconds: int
    main_banner_path: str


@dataclass(frozen=True, slots=True)
class SQLiteSettings:
    """SQLite settings."""

    path: str
    busy_timeout_ms: int
    foreign_keys: bool


@dataclass(frozen=True, slots=True)
class MemorySettings:
    """In-memory runtime settings."""

    lock_ttl_seconds: int
    rate_limit_ttl_seconds: int


@dataclass(frozen=True, slots=True)
class CryptAPISettings:
    """CryptAPI settings."""

    base_url: str
    callback_base_url: str
    request_timeout: int
    default_confirmations: int
    public_key_cache_ttl: int


@dataclass(frozen=True, slots=True)
class PaymentSettings:
    """Payment behavior settings."""

    invoice_ttl_minutes: int
    check_cooldown_seconds: int
    poll_interval_seconds: int
    poll_batch_size: int
    tolerance_coin: Decimal
    provider: str = "mock"


@dataclass(frozen=True, slots=True)
class RaitoSettings:
    """Raito feature gates."""

    devtools_enabled: bool
    hot_reload_enabled: bool
    repl_enabled: bool


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Top-level application settings."""

    app_name: str
    environment: Environment
    log_level: str
    store_base_currency: str
    bot: BotSettings
    sqlite: SQLiteSettings
    memory: MemorySettings
    cryptapi: CryptAPISettings
    payments: PaymentSettings
    raito: RaitoSettings
    fulfillment_encryption_key: str
    sentry_dsn: str | None
