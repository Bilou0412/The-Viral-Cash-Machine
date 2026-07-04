"""Authentification (Phase B.1) : hachage des mots de passe + bootstrap admin.

Le mot de passe n'est **jamais** stocké en clair : on garde un hash argon2. La
session utilisateur (cookie signé) est gérée par Starlette ``SessionMiddleware``
dans ``app.py`` ; ce module ne fait que le hachage et l'amorçage du compte admin.

En B.1 les clés API restent globales au process → seul l'``is_admin`` peut
dépenser (générer). En B.2 chaque utilisateur aura ses propres clés chiffrées.
"""

from __future__ import annotations

import os

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.engine import Engine
from sqlmodel import Session

from ...db.repositories import UserRepo

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Retourne un hash argon2 du mot de passe (jamais le mot de passe en clair)."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Vérifie un mot de passe contre son hash argon2 (False si non concordant)."""
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        # Hash corrompu / format inattendu → refuse plutôt que de crasher.
        return False


def bootstrap_admin(engine: Engine) -> None:
    """Crée le compte admin depuis ``VCM_ADMIN_EMAIL`` / ``VCM_ADMIN_PASSWORD``.

    No-op si les deux variables ne sont pas posées (cas des tests / du local) ou
    si l'email existe déjà. Appelé au démarrage (lifespan) une fois la DB prête.
    """
    email = os.environ.get("VCM_ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("VCM_ADMIN_PASSWORD", "")
    if not email or not password:
        return
    with Session(engine) as session:
        repo = UserRepo(session)
        if repo.get_by_email(email) is not None:
            return
        repo.create(email, hash_password(password), is_admin=True)
