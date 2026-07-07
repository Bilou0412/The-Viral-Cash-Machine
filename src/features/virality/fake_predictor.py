"""Prédicteur de viralité FAKE — déterministe, hors-ligne (dev + tests).

Heuristique transparente et STABLE (aucun réseau, aucun hasard) : chaque angle a un
poids de base, bonifié par la CONCISION de l'accroche (un hook court punche plus).
Donne des notes DISTINCTES par angle → le classement est significatif en test. La
vraie prédiction (LLM-juge / signal réel) vit dans `openai_predictor` puis, à terme,
dans la boucle de perfs réelles (le moat).
"""

from __future__ import annotations

from .model import HookVariant, ViralityScore

# Poids de base par angle (0..100) — l'ordre reflète le « punch » attendu.
_ANGLE_WEIGHT: dict[str, float] = {
    "promesse choc": 82.0,
    "in medias res": 78.0,
    "compte à rebours": 74.0,
    "question directe": 70.0,
    "POV": 66.0,
}
_IDEAL_WORDS = 8   # longueur d'accroche « idéale » (au-delà, on perd du punch)


class FakeViralityPredictor:
    """Implémente `ViralityPredictor` sans réseau (heuristique déterministe)."""

    def score(self, variant: HookVariant) -> ViralityScore:
        base = _ANGLE_WEIGHT.get(variant.angle, 60.0)
        words = len(variant.hook_text.split())
        concision = max(0.0, 10.0 - float(max(0, words - _IDEAL_WORDS)))
        hook_strength = min(100.0, base + concision)
        retention_risk = max(0.0, 40.0 - (hook_strength - 60.0))
        overall = round(hook_strength * 0.7 + (100.0 - retention_risk) * 0.3, 1)
        return ViralityScore(
            overall=overall,
            hook_strength=round(hook_strength, 1),
            retention_risk=round(retention_risk, 1),
            rationale=f"angle « {variant.angle} », accroche de {words} mots",
        )
