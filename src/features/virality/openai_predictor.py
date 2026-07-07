"""Prédicteur de viralité OpenAI — LLM-juge (0..100 + décomposition).

Note UNE variante de hook. C'est un proxy en attendant la boucle de perfs RÉELLES
(le moat) : quand des vidéos publiées auront de la donnée, le juge sera recalibré /
remplacé par le signal réel. Import `openai` paresseux (factory du service).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, ValidationError

from .model import HookVariant, ViralityScore
from .ports import ViralityError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


class _ScoreOut(BaseModel):
    model_config = ConfigDict(extra="ignore")

    overall: float = 0.0
    hook_strength: float = 0.0
    retention_risk: float = 0.0
    rationale: str = ""


class OpenAIViralityPredictor:
    """Implémente `ViralityPredictor` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def score(self, variant: HookVariant) -> ViralityScore:
        system = (
            "You rate the predicted virality of a short-form (9:16) video HOOK — the "
            "first ~2 seconds. Judge scroll-stopping power and retention. Be a harsh, "
            "calibrated critic.\n"
            'Return JSON {"overall"(0-100),"hook_strength"(0-100),'
            '"retention_risk"(0-100, higher = more drop-off),"rationale"(one short '
            "sentence)}. Output JSON only."
        )
        user = (
            f"Angle: {variant.angle}\nHook line: {variant.hook_text}\n"
            f"Opening frame: {variant.first_shot_prompt}\nRate it."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # réseau / clé / quota
            raise ViralityError(
                "La prédiction de viralité a échoué (vérifie ta clé OpenAI, le modèle "
                f"et tes quotas). Détail : {e}"
            ) from e
        content = resp.choices[0].message.content or ""
        try:
            out = _ScoreOut.model_validate_json(content)
        except ValidationError as e:
            raise ViralityError("Note de viralité illisible.") from e
        return ViralityScore(
            overall=_clamp(out.overall),
            hook_strength=_clamp(out.hook_strength),
            retention_risk=_clamp(out.retention_risk),
            rationale=out.rationale,
        )
