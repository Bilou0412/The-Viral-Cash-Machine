"""Génération réelle d'un épisode Aventure complet via les services du studio.

Chaîne connectée : script (Fake grotte/mine) → assets image-first (Replicate réel)
→ montage MoviePy (timers + plaques de noms + sous-titres conteur).
Sortie : studio_output/.../final_video.mp4
"""

import os
import time

# Sortie user-writable + DB locale.
os.environ.setdefault("VCM_OUTPUT_DIR", "./studio_output")
os.environ.setdefault("VCM_STUDIO_DB", "sqlite:///studio.db")

# Clés depuis .env.
for line in open(".env"):
    line = line.strip()
    if "=" in line and (line.startswith("REPLICATE") or line.startswith("OPENAI")):
        k, v = line.split("=", 1)
        os.environ[k] = v.strip().strip('"').strip("'")

from sqlmodel import Session  # noqa: E402

from src.features.scripting.fake_adventure_decomposer import (  # noqa: E402
    FakeAdventureDecomposer,
)
from src.studio.api.events import bus  # noqa: E402
from src.studio.api.services.generation import AssetGenerationService  # noqa: E402
from src.studio.api.services.montage import MontageService  # noqa: E402
from src.studio.db.engine import get_engine, init_db  # noqa: E402
from src.studio.db.repositories import (  # noqa: E402
    EpisodeRepo,
    ProjectRepo,
    ScriptRepo,
)

t0 = time.time()
engine = get_engine()
init_db(engine)

script = FakeAdventureDecomposer().decompose_adventure("grotte hantée", "Étienne", "Marc")
with Session(engine) as s:
    proj = ProjectRepo(s).create(name="demo-reel")
    pid = proj.id
    epi = EpisodeRepo(s).create(project_id=pid, title="Grotte hantée", draft_mode=True)
    eid = epi.id
    ScriptRepo(s).create(episode_id=eid, script_json=script.model_dump_json())
print(f"[setup] projet={pid} épisode={eid} (draft)", flush=True)

# Trace de progression via le bus SSE.
def _on_event(ev):
    t = ev.get("type")
    if t == "asset_started":
        print(f"  → {ev.get('index')}: {ev.get('beat')} ({ev.get('kind')})...", flush=True)
    elif t == "asset_failed":
        print(f"  ✗ FAIL {ev.get('asset_id')}: {ev.get('error')}", flush=True)
    elif t == "generation_done":
        print(f"[assets] terminés ({ev.get('total')} assets)", flush=True)

try:
    bus.subscribe(eid, _on_event)  # best-effort, selon l'API du bus
except Exception:
    pass

print("[generate] lancement génération réelle (image-first, Replicate)...", flush=True)
AssetGenerationService(engine).generate_episode(eid, script, "left")
print(f"[generate] OK en {int(time.time()-t0)}s", flush=True)

print("[montage] assemblage MoviePy (timers + noms + sous-titres)...", flush=True)
out = MontageService(engine).assemble_rich(eid)
print("[montage] OK", flush=True)
print(f"FINAL_VIDEO={out}", flush=True)
print(f"[done] total {int(time.time()-t0)}s", flush=True)
