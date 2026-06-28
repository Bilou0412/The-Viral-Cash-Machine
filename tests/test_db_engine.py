"""Offline tests for the dialect-agnostic engine (SQLite default, Postgres-ready).

No real Postgres connection: we only assert URL normalization and that engines
build with the right dialect/driver. SQLite stays the default everywhere.
"""

from __future__ import annotations

import pytest

from src.studio.db.engine import _normalize_url, get_engine


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://x", "postgresql+psycopg://x"),  # explicit driver kept
        ("sqlite:///studio.db", "sqlite:///studio.db"),
        ("sqlite:///:memory:", "sqlite:///:memory:"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert _normalize_url(raw) == expected


def test_sqlite_engine_builds() -> None:
    eng = get_engine("sqlite:///:memory:")
    assert eng.dialect.name == "sqlite"


def test_postgres_engine_uses_psycopg_without_connecting() -> None:
    # Bare postgres:// URL must select the psycopg v3 driver (not the absent psycopg2)
    # and build without opening a connection.
    eng = get_engine("postgres://u:p@localhost:5432/db")
    assert eng.dialect.name == "postgresql"
    assert eng.dialect.driver == "psycopg"
