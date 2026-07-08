"""Modèles de CONTENU du décrypteur de scènes (v5 — architecture 3 niveaux).

Sortie de l'IA, alignée sur les 3 conteneurs de l'éditeur (`VideoPlan → ScenePlan
→ ShotPlan` ≙ `EditorDocument → Scene → ClipBrick`). On **réutilise les sous-modèles**
de `editor.document` (Cadre, Camera, Lumiere…) ; seule différence : au niveau plan les
personnages sont **par nom** (`ShotCharacterPlan`) — `scene_plan_to_document` résout
name→ref bible en `PersonnagePresent`. Convention : ``*_desc`` EN, narration FR.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ...editor.document import (
    Cadre,
    Camera,
    Continuite,
    ElementSecondaire,
    IntentionGlobale,
    LocationEntry,
    Lumiere,
    LumiereTemps,
    Physique,
    Profondeur,
    RenderMeta,
    Segment,
    Son,
)


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShotCharacterPlan(_M):
    """Un personnage présent dans un plan, PAR NOM (résolu en `ref` bible ensuite).
    Ne porte que le JEU du plan — jamais l'apparence (héritée de la bible)."""

    name: str = ""
    action: str = ""
    trajectoire: str = ""
    vitesse: str = ""
    expression: str = ""
    etat_debut: str = ""
    etat_fin: str = ""


class ShotPlan(_M):
    """Un PLAN (1 prise i2v) : le brief v5 en version décomposeur (persos par nom)."""

    id: str
    kind: Literal["video", "photo"] = "video"
    duree_s: float = 4.0
    narration_fr: str = ""            # FR — → son.dialogue_voix + enfant audio
    start_image: str = ""
    sujet: str = ""                   # sujet LIBRE EN (plan non « perso-dans-décor »)
    cadre: Cadre = Field(default_factory=Cadre)
    profondeur: Profondeur = Field(default_factory=Profondeur)
    camera: Camera = Field(default_factory=Camera)
    personnages: list[ShotCharacterPlan] = Field(default_factory=list)
    elements_secondaires: list[ElementSecondaire] = Field(default_factory=list)
    physique_environnement: list[Physique] = Field(default_factory=list)
    lumiere_override: Lumiere | None = None
    lumiere_temps: LumiereTemps = Field(default_factory=LumiereTemps)
    son: Son = Field(default_factory=Son)
    timeline: list[Segment] = Field(default_factory=list)
    intention_plan: str = ""
    continuite: Continuite = Field(default_factory=Continuite)


class ScenePlan(_M):
    """Une SCÈNE : référence un décor (`location_ref`) + variation + plans."""

    id: str
    title: str = ""
    environment_desc: str = ""        # EN — prompt de la photo d'établissement
    location_ref: str = ""
    saison: str = ""
    moment_jour: str = ""
    meteo: str = ""
    lumiere_ambiante: Lumiere = Field(default_factory=Lumiere)
    mood: str = ""
    ambiance_sonore: str = ""         # room tone hérité par les plans
    intention_scene: str = ""
    shots: list[ShotPlan] = Field(default_factory=list)


class CharacterPlan(_M):
    """Fiche bible perso, PAR NOM (id assigné par `scene_plan_to_document`)."""

    name: str = ""
    appearance: str = ""
    wardrobe: str = ""
    voice_id: str = ""
    traits: str = ""


class VideoPlan(_M):
    """La VIDÉO : contenant (méta) + intention + bibles réutilisables + scènes."""

    title: str = "Nouvelle vidéo"
    meta: RenderMeta = Field(default_factory=RenderMeta)
    intention_globale: IntentionGlobale = Field(default_factory=IntentionGlobale)
    musique_score: str = ""
    location_bible: list[LocationEntry] = Field(default_factory=list)
    cast: list[CharacterPlan] = Field(default_factory=list)   # bible perso (par nom)
    scenes: list[ScenePlan] = Field(default_factory=list)

    # Compat : certains appelants lisent `.character_bible` (alias de `cast`).
    @property
    def character_bible(self) -> list[CharacterPlan]:
        return self.cast
