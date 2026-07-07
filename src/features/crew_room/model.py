"""Modèles de la table ronde — créer UNE scène par la discussion de l'équipe.

L'unité de création est la SCÈNE. Les métiers (voix) débattent en plusieurs tours,
puis on SYNTHÉTISE la scène structurée (format v4 : `ScenePlan` + persos bible).
Le transcript (le « thinking ») est conservé pour la mémoire et la revue.

Réutilise le format de sortie du chemin scènes (`ScenePlan`/`CharacterPlan`) : la
table ronde REMPLACE la voix unique « réalisateur » du décrypteur micro, pas le
format. Feature pure (pydantic uniquement).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from ..scenes.model import CharacterPlan, ScenePlan


class SceneBrief(BaseModel):
    """Le squelette d'une scène (issu de l'arc du scénariste) donné à la table ronde."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    intention: str = ""      # ce qui se passe et pourquoi ça compte pour l'arc
    environment: str = ""    # amorce de décor (EN), si le scénariste en a posé une


class RoomMemory(BaseModel):
    """La mémoire qui AVANCE de scène en scène (continuité + bible cumulée)."""

    model_config = ConfigDict(extra="ignore")

    bible: list[CharacterPlan] = Field(default_factory=list)  # personnages déjà établis
    synopsis_so_far: str = ""   # résumé des scènes déjà créées
    continuity: str = ""        # notes de continuité (ce qu'il faut respecter)


class Turn(BaseModel):
    """Un tour de parole dans la table ronde (une voix = un métier)."""

    model_config = ConfigDict(extra="ignore")

    role: str = ""      # clé du CrewRole qui parle
    message: str = ""


class RoomResult(BaseModel):
    """Le fruit de la table ronde : la scène structurée + persos neufs + le débat."""

    model_config = ConfigDict(extra="ignore")

    scene: ScenePlan
    new_characters: list[CharacterPlan] = Field(default_factory=list)
    transcript: list[Turn] = Field(default_factory=list)
