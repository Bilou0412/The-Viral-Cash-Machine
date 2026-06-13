"""Filesystem layout for generated assets — single source of truth.

The base directory defaults to ``exports/`` (the project convention) but is
overridable via the ``VCM_OUTPUT_DIR`` environment variable. This matters in
environments where ``exports/`` is owned by another user (e.g. created by a
root Docker run): point ``VCM_OUTPUT_DIR`` at a writable directory instead of
chowning the original.
"""

import os

DEFAULT_OUTPUT_DIR = "exports"


def exports_base() -> str:
    """Root directory under which all episode assets are written."""
    return os.environ.get("VCM_OUTPUT_DIR", DEFAULT_OUTPUT_DIR)


def episode_dir(project_name: str, episode_id: int) -> str:
    """On-disk directory for one episode's assets."""
    return os.path.join(exports_base(), project_name, f"episode_{episode_id}")
