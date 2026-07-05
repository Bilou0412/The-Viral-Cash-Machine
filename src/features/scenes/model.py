"""Modèles de CONTENU du décrypteur de scènes (le plan de vidéo).

Neutres (aucun CYOA/horreur) et distincts de l'index `editor.document.Scene` :
ici c'est la sortie de l'IA (le contenu à générer), là-bas c'est le regroupement
de briques. Convention langue : ``*_desc`` = anglais (prompt visuel),
``*_fr`` = français (parlé).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShotPlan(_M):
    """Un plan court d'une scène (brique vidéo/photo)."""

    id: str
    kind: Literal["video", "photo"] = "video"
    visual_desc: str = ""     # EN — ce qu'on voit (prompt image / 1re frame)
    motion_desc: str = ""     # EN — le mouvement (vidéo)
    narration_fr: str = ""    # FR — narration du plan
    duration_s: float = 4.0   # court (contexte concentré)


class ScenePlan(_M):
    """Une scène : contexte figé (photo d'environnement) + plans courts."""

    id: str
    title: str = ""
    environment_desc: str = ""  # EN — la photo d'environnement (contexte figé)
    context_text: str = ""      # récit concentré de la scène (FR)
    art_direction: str = ""
    shots: list[ShotPlan] = Field(default_factory=list)


class VideoPlan(_M):
    """La vidéo entière : une séquence de scènes (l'arc)."""

    title: str = "Nouvelle vidéo"
    global_context: str = ""
    characters: dict[str, str] = Field(default_factory=dict)
    art_direction: str = ""
    scenes: list[ScenePlan] = Field(default_factory=list)
