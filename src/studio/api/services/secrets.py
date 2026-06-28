"""BYOK API keys entered in the app (Settings page).

Stores the user's OpenAI / Replicate keys in the DB (on the volume, so they
survive redeploys) and injects them into ``os.environ`` — so every existing
``os.environ.get(...)`` read and the Replicate SDK pick them up without any
refactor. Single-tenant self-host; per-user + encryption arrive with auth (B/E).
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.engine import Engine

from ...db.engine import get_session
from ...db.repositories import SettingRepo

MANAGED_KEYS = ("OPENAI_API_KEY", "REPLICATE_API_TOKEN")


def apply_to_env(engine: Engine) -> None:
    """Load stored keys into the process environment (call at startup)."""
    with get_session(engine) as session:
        repo = SettingRepo(session)
        for k in MANAGED_KEYS:
            v = repo.get(k)
            if v:
                os.environ[k] = v


def set_keys(
    engine: Engine,
    openai: Optional[str] = None,
    replicate: Optional[str] = None,
) -> None:
    """Persist the non-empty keys to the DB and apply them to ``os.environ``."""
    pairs = {"OPENAI_API_KEY": openai, "REPLICATE_API_TOKEN": replicate}
    with get_session(engine) as session:
        repo = SettingRepo(session)
        for k, v in pairs.items():
            if v:  # ignore empty/None so a blank field never wipes an existing key
                repo.set(k, v)
                os.environ[k] = v


def keys_status(engine: Engine) -> dict[str, bool]:
    """Which keys are configured (DB or env). Never returns the secret itself."""
    with get_session(engine) as session:
        repo = SettingRepo(session)
        return {
            "openai_set": bool(
                repo.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
            ),
            "replicate_set": bool(
                repo.get("REPLICATE_API_TOKEN")
                or os.environ.get("REPLICATE_API_TOKEN")
            ),
        }
