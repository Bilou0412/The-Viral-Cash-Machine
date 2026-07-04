"""Export MP4 d'un document éditeur via le package Node Remotion (subprocess).

Résout le document en `RenderModel` avec des **URLs absolues** vers l'API (pour que
le Chromium headless de Remotion puisse fetch les assets), écrit les props JSON, puis
lance `node render/dist/cli.js --props <json> --out <mp4>`.

Best-effort : toute erreur (Node absent, `render/dist` non buildé, échec du rendu) →
événement SSE d'échec + exception loggée par la BackgroundTask — jamais de crash serveur.
Le rendu réel nécessite Node + Chromium dans l'image (cf. Dockerfile) ; en local hors
conteneur, l'appel échoue proprement (la route reste schedulable).
"""

from __future__ import annotations

import json
import os
import subprocess

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....editor import upgrade_document
from ....editor.resolve import resolve
from ...db.repositories import AssetRepo, EditorDocRepo, ProjectRepo
from ..events import bus
from .paths import editor_dir

# .../src/studio/api/services/remotion_render.py → racine du dépôt (4 niveaux).
_REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
_RENDER_CLI = os.path.join(_REPO_ROOT, "render", "dist", "cli.js")


def _render_base() -> str:
    """Base URL absolue depuis laquelle Remotion fetch les assets (même conteneur)."""
    return os.environ.get("VCM_RENDER_BASE", "http://localhost:8000").rstrip("/")


def render_document(engine: Engine, doc_id: int) -> str | None:
    """Rend le MP4 final d'un document éditeur ; renvoie le chemin (ou lève)."""
    with Session(engine) as session:
        row = EditorDocRepo(session).get(doc_id)
        if row is None:
            raise ValueError(f"editor document {doc_id} not found")
        doc = upgrade_document(json.loads(row.doc_json))
        assets = list(AssetRepo(session).assets_by_document(doc_id))
        project = ProjectRepo(session).get(row.project_id)
        project_name = project.name if project else f"project_{row.project_id}"

    base = _render_base()
    asset_src = {
        a.beat: f"{base}/api/assets/{a.id}/file"
        for a in assets
        if a.status == "ready" and not a.excluded and a.id is not None
    }
    model = resolve(doc, asset_src)

    out_dir = editor_dir(project_name, doc_id)
    os.makedirs(out_dir, exist_ok=True)
    props_path = os.path.join(out_dir, "render_model.json")
    with open(props_path, "w", encoding="utf-8") as fh:
        fh.write(model.model_dump_json())
    out_path = os.path.join(out_dir, "final_video.mp4")

    bus.publish(doc_id, {"type": "produce_started"})
    try:
        subprocess.run(
            ["node", _RENDER_CLI, "--props", props_path, "--out", out_path],
            check=True,
            capture_output=True,
            text=True,
            cwd=_REPO_ROOT,
        )
    except Exception as exc:  # node absent / rendu échoué → SSE + remonte
        bus.publish(
            doc_id,
            {"type": "asset_failed", "asset_id": 0, "error": f"render: {exc}"},
        )
        raise
    bus.publish(doc_id, {"type": "produce_done", "final_path": out_path})
    return out_path
