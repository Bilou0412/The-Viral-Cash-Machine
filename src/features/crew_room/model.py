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

from ..scenes.model import CharacterPlan, ScenePlan, ShotCharacterPlan


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


class ContractShot(BaseModel):
    """Un plan du CONTRAT : un trou à remplir (id + intention + type)."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    beat: str = ""     # à quoi sert ce plan (intention), en clair
    kind: str = "video"


class SceneContract(BaseModel):
    """La scène À TROUS que le réalisateur pose : la liste des plans à remplir."""

    model_config = ConfigDict(extra="ignore")

    env_intention: str = ""             # ce que doit montrer la photo d'environnement
    shots: list[ContractShot] = Field(default_factory=list)


class Draft(BaseModel):
    """Le BROUILLON d'un métier : il ne remplit QUE les champs qu'il possède.

    `env` = trous au niveau scène (décor/lumière de la photo d'env). `shots` =
    trous par plan (`{shot_id: {champ: valeur}}`). `new_characters` /
    `shot_characters` = réservés au casting.
    """

    model_config = ConfigDict(extra="ignore")

    department: str = ""
    env: dict[str, str] = Field(default_factory=dict)
    shots: dict[str, dict[str, str]] = Field(default_factory=dict)
    new_characters: list[CharacterPlan] = Field(default_factory=list)
    shot_characters: dict[str, list[ShotCharacterPlan]] = Field(default_factory=dict)


class Turn(BaseModel):
    """Une contribution affichée (le contrat, ou le brouillon d'un métier)."""

    model_config = ConfigDict(extra="ignore")

    role: str = ""      # clé du CrewRole (ou 'realisateur' pour le contrat)
    message: str = ""


class ReviewVerdict(BaseModel):
    """Le verdict du SUPERVISEUR sur la scène assemblée : valider, ou renvoyer corriger.

    `redo` = {département -> consigne} : les SEULS départements à refaire (révision
    ciblée), avec la note du superviseur. `ok=True` et `redo` vide ⇒ la scène est
    validée, on clôt la boucle. C'est ce verdict qui « orchestre les protagonistes »."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    redo: dict[str, str] = Field(default_factory=dict)
    note: str = ""   # commentaire global (affiché dans le transcript)


class RoomResult(BaseModel):
    """Le fruit de la table ronde : la scène structurée + persos neufs + le débat."""

    model_config = ConfigDict(extra="ignore")

    scene: ScenePlan
    new_characters: list[CharacterPlan] = Field(default_factory=list)
    transcript: list[Turn] = Field(default_factory=list)
