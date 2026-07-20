"""Per-environment configuration for VCM Studio.

Single place that reads environment variables, with defaults equal to the
current local behaviour. Production environments (Fly dev/prod) override these
via env vars / secrets — see docs/DEPLOY.md. No cloud logic lives here.
"""

from __future__ import annotations

import os

_DEFAULT_CORS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def cors_origins() -> list[str]:
    """Allowed browser origins.

    Reads ``CORS_ORIGINS`` (comma-separated). Empty/unset -> the local dev
    defaults, so behaviour is unchanged unless the env var is provided.
    """
    raw = os.environ.get("CORS_ORIGINS", "").strip()
    if not raw:
        return list(_DEFAULT_CORS)
    return [o.strip() for o in raw.split(",") if o.strip()]
