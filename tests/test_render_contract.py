"""Contrat Python ↔ Node : un `RenderModel` pydantic valide le schéma zod de render/.

Garde-fou anti-dérive entre `src/editor/render_model.py` et `render/src/renderModel.ts`.
Gated : ne tourne que là où Node + `render/node_modules` existent (Docker/CI). Sinon skip.
"""

import os
import shutil
import subprocess

import pytest

pytest.importorskip("pydantic")

from src.editor.render_model import RenderClip, RenderModel, SubtitleWord

_RENDER_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "render"))


def _node_ready() -> bool:
    return bool(shutil.which("npx")) and os.path.isdir(
        os.path.join(_RENDER_DIR, "node_modules")
    )


@pytest.mark.skipif(
    not _node_ready(), reason="render/ node_modules absent (Docker/CI uniquement)"
)
def test_python_render_model_passes_node_zod(tmp_path):
    model = RenderModel(
        clips=(
            RenderClip(
                id="a", media="video", src="/api/assets/1/file", start=0.0, duration=2.0,
                subtitles=(SubtitleWord(text="hi", start=0.0, end=0.5),),
            ),
            RenderClip(
                id="b", media="text", start=0.0, duration=1.0, text="T",
                style={"color": "white"}, z=3,
            ),
            RenderClip(
                id="c", media="overlay", src="/api/assets/2/file", start=0.0,
                duration=1.0, transform={"opacity": 0.5},
            ),
        ),
        total_duration=2.0,
    )
    f = tmp_path / "rm.json"
    f.write_text(model.model_dump_json(), encoding="utf-8")
    script = (
        "import {readFileSync} from 'fs';"
        "import {RenderModelSchema} from './src/renderModel';"
        "RenderModelSchema.parse(JSON.parse(readFileSync(process.argv[1],'utf8')));"
        "console.log('OK');"
    )
    proc = subprocess.run(
        ["npx", "tsx", "-e", script, str(f)],
        cwd=_RENDER_DIR, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "OK" in proc.stdout
