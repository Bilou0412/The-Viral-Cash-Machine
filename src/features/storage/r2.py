"""Cloudflare R2 (S3-compatible) backend. Refs are object keys.

Enabled by ``STORAGE_BACKEND=r2`` + ``R2_*`` env vars. boto3 is imported lazily
so local/test runs never need it. Serving is proxied/redirected by the app (no
presigned URL handed to the browser) — see docs/DEPLOY.md.
"""

from __future__ import annotations

import os
import posixpath
from typing import Any, Optional

from starlette.responses import RedirectResponse, Response, StreamingResponse

from ...infra.download import download_file
from .ports import StoragePort


def _output_base() -> str:
    # Mirror studio paths.exports_base() without importing studio (keep features
    # decoupled): the local cache root for materialized objects.
    return os.environ.get("VCM_OUTPUT_DIR", "exports")


def _key_for(folder: str, filename: str) -> str:
    """Deterministic object key from a local folder/filename under the output base."""
    rel = os.path.relpath(folder, _output_base())
    parts = [p for p in rel.replace(os.sep, "/").split("/") if p not in ("", ".")]
    return posixpath.join(*parts, filename) if parts else filename


class R2Storage(StoragePort):
    def __init__(
        self,
        *,
        endpoint: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        public_base: Optional[str] = None,
    ) -> None:
        self._bucket = bucket
        self._public_base = public_base.rstrip("/") if public_base else None
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._client: Any = None

    @property
    def client(self) -> Any:
        if self._client is None:
            import boto3  # lazy: only the r2 backend needs it
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name="auto",
                config=Config(signature_version="s3v4"),
            )
        return self._client

    def persist_from_url(self, url: str, folder: str, filename: str) -> Optional[str]:
        # Download to the local cache first (reuses the existing helper), then
        # upload. The local copy doubles as the materialize() cache for this run.
        local = download_file(url, folder, filename)
        if local is None:
            return None
        key = _key_for(folder, filename)
        self.client.upload_file(local, self._bucket, key)
        return key

    def persist_file(self, src_path: str, folder: str, filename: str) -> str:
        key = _key_for(folder, filename)
        self.client.upload_file(src_path, self._bucket, key)
        return key

    def exists(self, ref: str) -> bool:
        if not ref:
            return False
        try:
            head = self.client.head_object(Bucket=self._bucket, Key=ref)
        except Exception:
            return False
        return int(head.get("ContentLength", 0)) > 0

    def materialize(self, ref: str) -> str:
        dest = os.path.join(_output_base(), ref)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            return dest
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        self.client.download_file(self._bucket, ref, dest)
        return dest

    def serve(self, ref: str, filename: Optional[str] = None) -> Response:
        if self._public_base:
            # Stable, CDN-cached, same asset — no signature to expire.
            return RedirectResponse(f"{self._public_base}/{ref}", status_code=307)
        # Private bucket: stream through the app (still same-origin for the client).
        obj = self.client.get_object(Bucket=self._bucket, Key=ref)
        return StreamingResponse(
            obj["Body"].iter_chunks(),
            media_type=obj.get("ContentType", "application/octet-stream"),
        )
