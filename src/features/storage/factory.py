"""Backend selection + a thin module-level façade.

Callers use ``storage.exists(ref)`` / ``materialize`` / ``serve`` /
``persist_from_url`` without knowing which backend is active. Default = local
(byte-identical to the historical behaviour); ``STORAGE_BACKEND=r2`` switches.
"""

from __future__ import annotations

import os
from typing import Optional

from starlette.responses import Response

from .local import LocalStorage
from .ports import StoragePort

_backend: Optional[StoragePort] = None


def _build() -> StoragePort:
    if os.environ.get("STORAGE_BACKEND", "local").strip().lower() == "r2":
        from .r2 import R2Storage

        return R2Storage(
            endpoint=os.environ["R2_ENDPOINT"],
            bucket=os.environ["R2_BUCKET"],
            access_key=os.environ["R2_ACCESS_KEY_ID"],
            secret_key=os.environ["R2_SECRET_ACCESS_KEY"],
            public_base=os.environ.get("R2_PUBLIC_BASE"),
        )
    return LocalStorage()


def get_storage() -> StoragePort:
    """Return the process storage backend (built once)."""
    global _backend
    if _backend is None:
        _backend = _build()
    return _backend


def set_storage(backend: Optional[StoragePort]) -> None:
    """Override the backend (tests). ``None`` resets to the env-configured one."""
    global _backend
    _backend = backend


# -- façade -----------------------------------------------------------------

def persist_from_url(url: str, folder: str, filename: str) -> Optional[str]:
    return get_storage().persist_from_url(url, folder, filename)


def persist_file(src_path: str, folder: str, filename: str) -> str:
    return get_storage().persist_file(src_path, folder, filename)


def exists(ref: str) -> bool:
    return get_storage().exists(ref)


def materialize(ref: str) -> str:
    return get_storage().materialize(ref)


def serve(ref: str, filename: Optional[str] = None) -> Response:
    return get_storage().serve(ref, filename)
