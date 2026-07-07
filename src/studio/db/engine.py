"""Database engine, schema init and session factory for VCM Studio.

Default database is SQLite at the repo root (``studio.db``) — used everywhere by
default (local, tests, CI). Override with ``VCM_STUDIO_DB`` *or* ``DATABASE_URL``
(Fly Managed Postgres / Neon / Supabase inject the latter). A bare
``postgres://`` / ``postgresql://`` URL is rewritten to ``postgresql+psycopg://``
so SQLAlchemy uses psycopg v3 (psycopg2 is intentionally not a dependency).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Default on-disk database at the repository root.
DEFAULT_DB_URL = "sqlite:///studio.db"

_engine: Engine | None = None


def _normalize_url(url: str) -> str:
    """Rewrite bare Postgres URLs to use the psycopg v3 driver.

    Managed providers hand out ``postgres://`` or ``postgresql://`` which make
    SQLAlchemy pick the (absent) psycopg2 driver. Force the psycopg v3 driver.
    Leaves any explicit ``+driver`` and non-Postgres URLs untouched.
    """
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def _db_url() -> str:
    """Resolve the database URL: VCM_STUDIO_DB, then DATABASE_URL, then default."""
    raw = (
        os.environ.get("VCM_STUDIO_DB")
        or os.environ.get("DATABASE_URL")
        or DEFAULT_DB_URL
    )
    return _normalize_url(raw)


def _make_engine(url: str) -> Engine:
    """Build an engine with dialect-appropriate args (SQLite vs Postgres)."""
    is_sqlite = url.startswith("sqlite")
    kwargs: dict[str, Any] = {}
    if is_sqlite:
        # Allow cross-thread use of the single SQLite connection (FastAPI).
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Postgres over a managed proxy: validate connections before use and
        # recycle them so dropped server-side connections don't surface as errors.
        kwargs["pool_pre_ping"] = True
        kwargs["pool_recycle"] = 1800
    return create_engine(url, **kwargs)


def get_engine(url: str | None = None) -> Engine:
    """Return the shared engine, creating it on first use.

    Passing an explicit ``url`` always builds a fresh engine for that URL (handy
    for tests) without replacing the cached default engine.
    """
    global _engine
    if url is not None:
        return _make_engine(_normalize_url(url))
    if _engine is None:
        _engine = _make_engine(_db_url())
    return _engine


# Colonnes ajoutées après coup (LOT 2) — pour les DB SQLite déjà existantes :
# create_all ne fait PAS d'ALTER TABLE. (table, colonne, type SQL, défaut SQL).
_ADDED_COLUMNS = [
    ("episode", "theme", "VARCHAR", "'horror'"),
    ("asset", "excluded", "BOOLEAN", "0"),
    ("asset", "editor_document_id", "INTEGER", "NULL"),
    ("cost_entry", "source", "VARCHAR", "'estimate'"),
    ("cost_entry", "is_estimate", "BOOLEAN", "1"),
    ("cost_entry", "predict_time_s", "FLOAT", "NULL"),
    ("project", "owner_id", "INTEGER", "NULL"),  # B.2 multi-tenant
    ("editor_document", "distribution_json", "VARCHAR", "NULL"),  # fiche de sortie
    ("episode", "brief_json", "VARCHAR", "NULL"),  # brief du producteur
    ("editor_document", "memory_json", "VARCHAR", "NULL"),  # état table ronde
]


def _ensure_columns(eng: Engine) -> None:
    """Migration légère idempotente : ajoute les colonnes manquantes (SQLite).

    SQLite-only : le SQL ``ALTER TABLE ... DEFAULT`` est SQLite-flavored. Sur
    Postgres, ``create_all`` crée déjà toutes les colonnes sur un schéma neuf
    (les évolutions ultérieures relèveront d'Alembic, cf. docs/DEPLOY.md).
    """
    from sqlalchemy import inspect, text

    if eng.dialect.name != "sqlite":
        return

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


def init_db(engine: Engine | None = None) -> Engine:
    """Create all tables on ``engine`` (or the shared engine). Idempotent."""
    eng = engine if engine is not None else get_engine()
    # Importing models registers them on SQLModel.metadata.
    from src.studio.db import models  # noqa: F401

    SQLModel.metadata.create_all(eng)
    _ensure_columns(eng)  # rattrape les colonnes ajoutées sur une DB existante
    return eng


@contextmanager
def get_session(engine: Engine | None = None) -> Iterator[Session]:
    """Yield a session bound to ``engine`` (or the shared engine)."""
    eng = engine if engine is not None else get_engine()
    with Session(eng) as session:
        yield session
