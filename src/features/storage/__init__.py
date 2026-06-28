"""Asset storage feature: local (default) or Cloudflare R2 object storage."""

from __future__ import annotations

from .factory import (
    exists,
    get_storage,
    materialize,
    persist_file,
    persist_from_url,
    serve,
    set_storage,
)
from .ports import StoragePort

__all__ = [
    "StoragePort",
    "get_storage",
    "set_storage",
    "persist_from_url",
    "persist_file",
    "exists",
    "materialize",
    "serve",
]
