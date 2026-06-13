"""Orchestration « un bouton = toute la vidéo ».

Enchaîne les 3 temps sur un épisode dont le script est déjà en base :
  1. génération des assets de l'AVENTURE (image-first, réf perso R2, chaînage R3),
  2. génération de l'INTRO (système historique : 2 persos + nameplates + timer),
  3. MONTAGE MoviePy (intro + 3 rounds + épilogue, vitesse R4, zoom R4b).

Séparé de `generate_episode`/`assemble_rich` pour garder ces briques pures et
testables hors-ligne ; cette orchestration fait de la vraie génération réseau.
"""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....features.scripting.adventure import AdventureScript
from ...db.repositories import ScriptRepo
from ..events import bus
from .generation import AssetGenerationService
from .intro import generate_intro
from .montage import MontageService


def produce_episode(engine: Engine, episode_id: int, side: str = "left") -> str:
    """Produit la vidéo COMPLÈTE d'un épisode (script déjà en base). Renvoie le mp4."""
    with Session(engine) as session:
        row = ScriptRepo(session).latest_for_episode(episode_id)
        if row is None:
            raise ValueError("no script for episode")
        script = AdventureScript.model_validate_json(row.script_json)

    bus.publish(episode_id, {"type": "produce_started"})
    # 1. Aventure (assets image-first).
    AssetGenerationService(engine).generate_episode(episode_id, script, side)
    # 2. Intro (système historique).
    generate_intro(engine, episode_id)
    # 3. Montage complet.
    out = MontageService(engine).assemble_rich(episode_id)
    bus.publish(episode_id, {"type": "produce_done", "final_path": out})
    return out
