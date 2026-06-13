"""R5b — production COMPLÈTE depuis le script GPT (Louis/Pierre, train-grotte).

Crée projet+épisode, stocke le script GPT (déjà généré dans /tmp/r5_script.json),
puis produit toute la vidéo : assets aventure (réf perso R2 + chaînage R3) +
intro (système historique) + montage MoviePy (vitesse R4, zoom R4b).
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

from src.studio.db.engine import get_engine, init_db  # noqa: E402
from src.studio.db.repositories import (  # noqa: E402
    EpisodeRepo, ProjectRepo, ScriptRepo,
)
from src.studio.api.services.produce import produce_episode  # noqa: E402
from src.features.scripting.adventure import AdventureScript  # noqa: E402

t0 = time.time()
engine = get_engine()
init_db(engine)
script = AdventureScript.model_validate_json(open("/tmp/r5_script.json").read())

with Session(engine) as s:
    proj = ProjectRepo(s).create(name="train-grotte")
    pid = proj.id
    epi = EpisodeRepo(s).create(project_id=pid, title="Train dans la grotte", draft_mode=True)
    eid = epi.id
    ScriptRepo(s).create(episode_id=eid, script_json=script.model_dump_json())
print(f"[setup] projet={pid} épisode={eid} (Louis tête d'horloge / Pierre tête de lune)", flush=True)

print("[produce] assets (réf perso + chaînage) + intro + montage... (~15-20 min)", flush=True)
out = produce_episode(engine, eid)
print(f"FINAL_VIDEO={out}", flush=True)
print(f"[done] total {int(time.time()-t0)}s", flush=True)
