"""Modèles de l'équipe (crew) — les artefacts que produisent les agents-métiers.

Pour l'instant : le **kit de distribution** (ce que produit l'attaché de presse /
Growth). Neutre, sans dépendance à l'éditeur (respect des couches : `features`
ne dépend pas de `studio`/`editor`).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DistributionKit(BaseModel):
    """La fiche de sortie d'une vidéo, écrite par l'attaché de presse / Growth.

    Titre accrocheur, description, hashtags et hook (première phrase qui retient).
    """

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    hook: str = ""


class SceneRef(BaseModel):
    """Ce que le directeur artistique reçoit par scène (l'entrée qu'il dirige)."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    title: str = ""
    environment: str = ""  # le prompt image actuel de la photo d'environnement


class SceneArt(BaseModel):
    """La direction artistique réécrite pour UNE scène (par le DA)."""

    model_config = ConfigDict(extra="ignore")

    scene_id: str = ""
    environment_prompt: str = ""  # prompt image EN réécrit de la photo d'environnement


class ArtDirection(BaseModel):
    """Ce que produit le directeur artistique : l'identité visuelle de la vidéo.

    L'`art_direction` globale (le style commun) + le prompt image réécrit de chaque
    photo d'environnement (la 1re frame de chaque plan). Langage EN (modèles image).
    """

    model_config = ConfigDict(extra="ignore")

    art_direction: str = ""
    scenes: list[SceneArt] = Field(default_factory=list)


class NarrationRef(BaseModel):
    """Une réplique que le dialoguiste réécrit (l'id relie au bon enfant audio)."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    text: str = ""


class DialogueLine(BaseModel):
    """Une réplique réécrite par le dialoguiste (rattachée par `line_id`)."""

    model_config = ConfigDict(extra="ignore")

    line_id: str = ""
    text: str = ""


class Dialogue(BaseModel):
    """Ce que produit le dialoguiste : les répliques réécrites (français), par id."""

    model_config = ConfigDict(extra="ignore")

    lines: list[DialogueLine] = Field(default_factory=list)


# -- Réalisateur : assemble une PARTIE (fragment v5) depuis une description NL ----


class NameplatePlan(BaseModel):
    """Une plaque de nom posée par le réalisateur (effet du catalogue)."""

    model_config = ConfigDict(extra="ignore")

    text: str = ""
    side: Literal["left", "right"] = "left"


class BeatPlan(BaseModel):
    """Un beat d'une PARTIE, tel que le réalisateur le pose — AVEC ses effets.

    Les effets sont CHOISIS dans le catalogue que l'agent voit (`AgentContext.effects`) :
    `eye_open` (transition d'établissement), `countdown` (écran timer flou), `nameplates`.
    Convention : `sujet` en anglais (prompt visuel), `narration_fr` en français (parlé)."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    kind: Literal["video", "photo"] = "photo"
    sujet: str = ""              # EN — sujet/prompt visuel du plan
    narration_fr: str = ""       # FR — texte parlé (voix off / réplique)
    duree_s: float = 3.0
    eye_open: bool = False        # effet : transition eye-open (établissement)
    countdown: bool = False       # effet : écran timer sur fond flouté (pas de narration)
    nameplates: list[NameplatePlan] = Field(default_factory=list)


class FragmentPlan(BaseModel):
    """Ce que produit le RÉALISATEUR : une PARTIE de vidéo (intro, aventure…) = une
    séquence de beats à effets, prête à devenir un fragment v5 (`fragment_to_bricks`)."""

    model_config = ConfigDict(extra="ignore")

    part: str = ""
    beats: list[BeatPlan] = Field(default_factory=list)
