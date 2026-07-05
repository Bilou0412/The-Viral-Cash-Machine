"""Clés API par-utilisateur, **chiffrées au repos** (Phase B.2).

Chaque utilisateur saisit ses propres clés OpenAI/Replicate (page Réglages) ;
elles sont chiffrées (Fernet, clé serveur ``VCM_SECRET_KEY``) et stockées en DB
(table ``user_api_key``). Elles ne sont **jamais** écrites dans ``os.environ``
(global = fuite entre utilisateurs) : la clé déchiffrée est distribuée **par
requête** et injectée dans le provider/décomposeur de l'appelant.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.fernet import Fernet
from fastapi import HTTPException
from sqlalchemy.engine import Engine

from ...db.engine import get_session
from ...db.repositories import UserApiKeyRepo


def _fernet() -> Fernet:
    """Construit le chiffreur depuis ``VCM_SECRET_KEY`` (requis pour (dé)chiffrer)."""
    key = os.environ.get("VCM_SECRET_KEY")
    if not key:
        raise HTTPException(500, "VCM_SECRET_KEY manquant (chiffrement des clés API)")
    try:
        return Fernet(key.encode())
    except Exception as e:
        raise HTTPException(
            500, "VCM_SECRET_KEY invalide (clé Fernet urlsafe-base64 de 32 octets attendue)"
        ) from e


@dataclass(frozen=True)
class UserKeys:
    """Clés déchiffrées d'un utilisateur (jamais persistées en clair)."""

    openai: str | None = None
    replicate: str | None = None


def set_keys(
    engine: Engine,
    user_id: int,
    openai: str | None = None,
    replicate: str | None = None,
) -> None:
    """Chiffre et persiste les clés non vides de l'utilisateur (blanc ne vide pas)."""
    fernet = _fernet()
    with get_session(engine) as session:
        repo = UserApiKeyRepo(session)
        for provider, value in (("openai", openai), ("replicate", replicate)):
            if value:
                repo.upsert(user_id, provider, fernet.encrypt(value.encode()).decode())


def get_user_keys(engine: Engine, user_id: int) -> UserKeys:
    """Déchiffre et renvoie les clés de l'utilisateur (pour injection par requête).

    Un utilisateur **sans** clé n'exige pas ``VCM_SECRET_KEY`` (on ne construit le
    chiffreur que s'il y a au moins une ligne à déchiffrer).
    """
    with get_session(engine) as session:
        repo = UserApiKeyRepo(session)
        openai_row = repo.get(user_id, "openai")
        replicate_row = repo.get(user_id, "replicate")
    if openai_row is None and replicate_row is None:
        return UserKeys()
    fernet = _fernet()
    return UserKeys(
        openai=(
            fernet.decrypt(openai_row.ciphertext.encode()).decode()
            if openai_row
            else None
        ),
        replicate=(
            fernet.decrypt(replicate_row.ciphertext.encode()).decode()
            if replicate_row
            else None
        ),
    )


def keys_status(engine: Engine, user_id: int) -> dict[str, bool]:
    """Quelles clés sont configurées (présence seule ; ne déchiffre jamais)."""
    with get_session(engine) as session:
        status = UserApiKeyRepo(session).status(user_id)
    return {
        "openai_set": status.get("openai", False),
        "replicate_set": status.get("replicate", False),
    }
