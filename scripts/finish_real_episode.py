"""Termine l'épisode 1 SANS regénérer les visuels déjà produits.

Génère uniquement les pistes audio (narration conteur) manquantes, puis monte
en MoviePy (timers + plaques de noms + sous-titres). Réutilise les 38 assets
visuels déjà sur disque (studio_output/) et en base.
"""

import os
import time

os.environ.setdefault("VCM_OUTPUT_DIR", "./studio_output")
os.environ.setdefault("VCM_STUDIO_DB", "sqlite:///studio.db")
for line in open(".env"):
    line = line.strip()
    if "=" in line and (line.startswith("REPLICATE") or line.startswith("OPENAI")):
        k, v = line.split("=", 1)
        os.environ[k] = v.strip().strip('"').strip("'")

from sqlmodel import Session  # noqa: E402

from src.features.scripting.adventure import AdventureScript  # noqa: E402
from src.studio.api.services.generation import AssetGenerationService  # noqa: E402
from src.studio.api.services.generation_plan import plan_episode_assets  # noqa: E402
from src.studio.api.services.montage import MontageService  # noqa: E402
from src.studio.db.engine import get_engine  # noqa: E402
from src.studio.db.repositories import (  # noqa: E402
    AssetRepo,
    EpisodeRepo,
    ProjectRepo,
    ScriptRepo,
)

t0 = time.time()
engine = get_engine()
EID = 1

with Session(engine) as s:
    epi = EpisodeRepo(s).get(EID)
    proj = ProjectRepo(s).get(epi.project_id)
    project_name = proj.name
    script = AdventureScript.model_validate_json(
        ScriptRepo(s).latest_for_episode(EID).script_json
    )
    existing_beats = {a.beat for a in AssetRepo(s).assets_by_episode(EID) if a.kind == "audio"}

svc = AssetGenerationService(engine)
out_dir = svc.export_dir(project_name, EID)
os.makedirs(out_dir, exist_ok=True)

audio_plan = [a for a in plan_episode_assets(script, "left") if a.kind == "audio"]
todo = [a for a in audio_plan if a.beat not in existing_beats]
print(f"[audio] {len(todo)} pistes narration conteur à générer...", flush=True)
for i, pa in enumerate(todo):
    svc._generate_one(EID, pa, out_dir, True, {}, i)
    print(f"  ✓ {pa.beat}", flush=True)
print(f"[audio] OK en {int(time.time()-t0)}s", flush=True)

print("[montage] MoviePy (timers + noms + sous-titres conteur)...", flush=True)
out = MontageService(engine).assemble_rich(EID)
print(f"FINAL_VIDEO={out}", flush=True)
print(f"[done] total {int(time.time()-t0)}s", flush=True)
