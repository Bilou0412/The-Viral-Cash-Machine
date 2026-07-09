"""Utilitaires partagés par les hooks Claude Code (repo-context-kit, adapté VCM).

Chaque hook reçoit un JSON sur stdin (session_id, cwd, hook_event_name, et selon
l'événement tool_name / tool_input / tool_output). On centralise ici la lecture
robuste + quelques helpers repo. Aucun hook ne doit lever : on rend toujours 0.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def read_event() -> dict:
    """Lit le JSON envoyé par Claude Code sur stdin (jamais lever)."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def project_dir() -> Path:
    """Racine du projet. Claude Code fournit CLAUDE_PROJECT_DIR."""
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()))


def state_dir() -> Path:
    d = project_dir() / ".claude" / "state"
    d.mkdir(parents=True, exist_ok=True)
    return d


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd or project_dir()),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
