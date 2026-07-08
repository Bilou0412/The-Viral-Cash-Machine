"""Génère l'intro (système historique) de l'épisode 1 et re-monte le tout."""

import os
import shutil
import time

os.environ.setdefault("VCM_OUTPUT_DIR", "./studio_output")
os.environ.setdefault("VCM_STUDIO_DB", "sqlite:///studio.db")
for line in open(".env"):
    line = line.strip()
    if "=" in line and (line.startswith("REPLICATE") or line.startswith("OPENAI")):
        k, v = line.split("=", 1)
        os.environ[k] = v.strip().strip('"').strip("'")

from sqlmodel import Session  # noqa: E402

from src.studio.api.services.intro import generate_intro  # noqa: E402
from src.studio.api.services.montage import MontageService  # noqa: E402
from src.studio.db.engine import get_engine  # noqa: E402
from src.studio.db.repositories import AssetRepo  # noqa: E402

t0 = time.time()
engine = get_engine()
EID = 1

# Évite les doublons d'intro si relancé.
with Session(engine) as s:
    for a in AssetRepo(s).assets_by_episode(EID):
        if a.beat == "intro":
            s.delete(a)
    s.commit()

print("[intro] génération (image 2 persos -> dialogue, narration conteur, compile)...", flush=True)
intro = generate_intro(engine, EID)
print(f"[intro] OK -> {intro} ({int(time.time()-t0)}s)", flush=True)

# Force un re-montage complet (intro + rounds + épilogue).
ep_dir = os.path.join(os.environ["VCM_OUTPUT_DIR"], "demo-reel", f"episode_{EID}")
shutil.rmtree(os.path.join(ep_dir, "_montage"), ignore_errors=True)
try:
    os.remove(os.path.join(ep_dir, "final_video.mp4"))
except OSError:
    pass

print("[montage] intro + 3 rounds + épilogue...", flush=True)
out = MontageService(engine).assemble_rich(EID)
print(f"FINAL_VIDEO={out}", flush=True)
print(f"[done] total {int(time.time()-t0)}s", flush=True)
