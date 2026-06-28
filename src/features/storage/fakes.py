"""In-memory storage backend for tests (no filesystem, no network)."""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from starlette.responses import Response

from .ports import StoragePort
from .r2 import _key_for


class FakeStorage(StoragePort):
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def persist_from_url(self, url: str, folder: str, filename: str) -> Optional[str]:
        key = _key_for(folder, filename)
        self.objects[key] = f"fake:{url}".encode()
        return key

    def persist_file(self, src_path: str, folder: str, filename: str) -> str:
        key = _key_for(folder, filename)
        with open(src_path, "rb") as f:
            self.objects[key] = f.read()
        return key

    def exists(self, ref: str) -> bool:
        return bool(self.objects.get(ref))

    def materialize(self, ref: str) -> str:
        fd, path = tempfile.mkstemp(suffix="_" + os.path.basename(ref))
        with os.fdopen(fd, "wb") as f:
            f.write(self.objects[ref])
        return path

    def serve(self, ref: str, filename: Optional[str] = None) -> Response:
        return Response(self.objects.get(ref, b""), media_type="application/octet-stream")
