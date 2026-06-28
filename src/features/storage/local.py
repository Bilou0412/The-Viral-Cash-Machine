"""Local filesystem backend — the default. Refs are absolute paths, so every
operation matches the historical behaviour exactly (no DB/asset migration)."""

from __future__ import annotations

import os
import shutil
from typing import Optional

from starlette.responses import FileResponse, Response

from ...infra.download import download_file
from .ports import StoragePort


class LocalStorage(StoragePort):
    def persist_from_url(self, url: str, folder: str, filename: str) -> Optional[str]:
        os.makedirs(folder, exist_ok=True)
        return download_file(url, folder, filename)

    def persist_file(self, src_path: str, folder: str, filename: str) -> str:
        os.makedirs(folder, exist_ok=True)
        dest = os.path.join(folder, filename)
        if os.path.abspath(src_path) != os.path.abspath(dest):
            shutil.copyfile(src_path, dest)
        return dest

    def exists(self, ref: str) -> bool:
        return bool(ref) and os.path.exists(ref) and os.path.getsize(ref) > 0

    def materialize(self, ref: str) -> str:
        return ref

    def serve(self, ref: str, filename: Optional[str] = None) -> Response:
        return FileResponse(ref, filename=filename)
