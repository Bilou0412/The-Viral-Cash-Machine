"""SQLite engine, schema init and session factory for VCM Studio.

Default database lives at the repo root as ``studio.db``. Override with the
``VCM_STUDIO_DB`` environment variable (e.g. ``sqlite:///:memory:`` for tests).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Default on-disk database at the repository root.
DEFAULT_DB_URL = "sqlite:///studio.db"

_engine: Optional[Engine] = None


def _db_url() -> str:
    """Resolve the database URL from the environment, falling back to default."""
    return os.environ.get("VCM_STUDIO_DB", DEFAULT_DB_URL)


def get_engine(url: Optional[str] = None) -> Engine:
    """Return the shared engine, creating it on first use.

    Passing an explicit ``url`` always builds a fresh engine for that URL (handy
    for tests) without replacing the cached default engine.
    """
    global _engine
    if url is not None:
        return create_engine(
            url, connect_args={"check_same_thread": False}
        )
    if _engine is None:
        _engine = create_engine(
            _db_url(), connect_args={"check_same_thread": False}
        )
    return _engine


# Colonnes ajoutées après coup (LOT 2) — pour les DB SQLite déjà existantes :
# create_all ne fait PAS d'ALTER TABLE. (table, colonne, type SQL, défaut SQL).
_ADDED_COLUMNS = [
    ("episode", "theme", "VARCHAR", "'horror'"),
    ("asset", "excluded", "BOOLEAN", "0"),
]


def _ensure_columns(eng: Engine) -> None:
    """Migration légère idempotente : ajoute les colonnes manquantes (SQLite)."""
    from sqlalchemy import inspect, text

    insp = inspect(eng)
    tables = set(insp.get_table_names())
    with eng.begin() as conn:
        for table, column, sqltype, default in _ADDED_COLUMNS:
            if table not in tables:
                continue  # create_all l'a déjà créée avec la colonne
            have = {c["name"] for c in insp.get_columns(table)}
            if column not in have:
                conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN {column} "
                        f"{sqltype} DEFAULT {default}"
                    )
                )


def init_db(engine: Optional[Engine] = None) -> Engine:
    """Create all tables on ``engine`` (or the shared engine). Idempotent."""
    eng = engine if engine is not None else get_engine()
    # Importing models registers them on SQLModel.metadata.
    from src.studio.db import models  # noqa: F401

    SQLModel.metadata.create_all(eng)
    _ensure_columns(eng)  # rattrape les colonnes ajoutées sur une DB existante
    return eng


@contextmanager
def get_session(engine: Optional[Engine] = None) -> Iterator[Session]:
    """Yield a session bound to ``engine`` (or the shared engine)."""
    eng = engine if engine is not None else get_engine()
    with Session(eng) as session:
        yield session
