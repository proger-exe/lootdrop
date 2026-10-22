"""SQLite connection and schema bootstrap."""

import sqlite3
from pathlib import Path

from app.config.models import SQLiteSettings


def connect_sqlite(settings: SQLiteSettings) -> sqlite3.Connection:
    """Open a configured SQLite connection."""

    path = Path(settings.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute(f"pragma busy_timeout = {settings.busy_timeout_ms}")
    if settings.foreign_keys:
        connection.execute("pragma foreign_keys = on")
    return connection


def initialize_schema(connection: sqlite3.Connection) -> None:
    """Apply the idempotent SQLite schema."""

    schema_path = Path(__file__).with_name("schema.sql")
    connection.executescript(schema_path.read_text(encoding="utf-8"))
    connection.commit()
