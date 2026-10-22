"""Tests for SQLite schema bootstrap."""

import sqlite3

from app.db.sqlite import initialize_schema


def test_initialize_schema_creates_core_tables() -> None:
    """Schema bootstrap creates the core persistent tables."""

    connection = sqlite3.connect(":memory:")
    initialize_schema(connection)
    tables = {
        row[0]
        for row in connection.execute(
            "select name from sqlite_master where type = 'table'",
        )
    }
    assert "users" in tables
    assert "payment_invoices" in tables
    assert "payment_poll_events" in tables
    assert "outbox_events" in tables
