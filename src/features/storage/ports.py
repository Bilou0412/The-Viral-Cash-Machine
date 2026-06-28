"""Storage port: persist / locate / serve generated assets.

One process uses one backend (``STORAGE_BACKEND``): ``local`` (default — a
directory, behaviour identical to the historical filesystem layout) or ``r2``
(Cloudflare R2 / any S3-compatible object store).

A *ref* is the opaque handle stored in the DB (``Asset.local_path``):
- local backend  -> an absolute filesystem path (unchanged from before),
- r2 backend     -> an object key.

Each backend interprets its own refs, so callers never branch on the backend:
they call ``exists`` / ``materialize`` / ``serve`` on the ref.
"""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from starlette.responses import Response


@runtime_checkable
class StoragePort(Protocol):
    def persist_from_url(self, url: str, folder: str, filename: str) -> Optional[str]:
        """Fetch ``url`` into ``folder``/``filename``; return its ref or None on failure."""
        ...

    def persist_file(self, src_path: str, folder: str, filename: str) -> str:
        """Persist a local file under ``folder``/``filename`` and return its ref."""
        ...

    def exists(self, ref: str) -> bool:
        """True if the ref points at a non-empty stored object."""
        ...

    def materialize(self, ref: str) -> str:
        """Return a local filesystem path for ``ref`` (for ffmpeg / Remotion).

        Identity for the local backend; a cached download for object stores.
        """
        ...

    def serve(self, ref: str, filename: Optional[str] = None) -> Response:
        """Return an HTTP response serving the object at ``ref``."""
        ...
