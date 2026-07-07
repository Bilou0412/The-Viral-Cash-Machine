"""Modèles de la boucle VIRALITÉ — variantes de hook + note prédite.

Le hook (les ~2 premières secondes) décide 90 % du sort d'un short. Au lieu de
publier UNE ouverture au hasard, on en génère **N variantes**, on **prédit** la
viralité de chacune, et on **classe** — l'humain n'approuve que la gagnante.
Convention : prompts visuels en anglais, accroche/texte en français.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HookVariant(_M):
    """Une variante du HOOK : un angle d'ouverture + son accroche + sa 1re image."""

    id: str
    angle: str = ""              # l'angle d'ouverture (ex. « in medias res », « POV »)
    hook_text: str = ""          # FR — la promesse/accroche dite ou affichée
    first_shot_prompt: str = ""  # EN — le prompt visuel de la 1re image (start i2v)


class ViralityScore(_M):
    """La viralité PRÉDITE d'une variante (0..100) + sa décomposition."""

    overall: float = 0.0         # note globale 0..100 (ce qui classe)
    hook_strength: float = 0.0   # force de l'accroche 0..100
    retention_risk: float = 0.0  # risque de décrochage 0..100 (haut = mauvais)
    rationale: str = ""          # pourquoi (une phrase)


class ScoredVariant(_M):
    """Une variante avec sa note (le couple manipulé par le classement)."""

    variant: HookVariant
    score: ViralityScore


class RankedHooks(_M):
    """Les variantes classées par viralité DÉCROISSANTE (la 1re = la gagnante)."""

    variants: list[ScoredVariant] = Field(default_factory=list)

    @property
    def winner(self) -> ScoredVariant | None:
        return self.variants[0] if self.variants else None
