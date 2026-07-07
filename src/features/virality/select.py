"""Classement des variantes — pur, déterministe (aucune I/O).

Génère la note de chaque variante via le prédicteur injecté, puis trie par viralité
décroissante. La 1re = la gagnante que l'humain approuve. Tri STABLE : à note égale,
l'ordre de génération est conservé (la 1re variante produite gagne les ex æquo)."""

from __future__ import annotations

from .model import HookVariant, RankedHooks, ScoredVariant
from .ports import ViralityPredictor


def rank_hooks(variants: list[HookVariant], predictor: ViralityPredictor) -> RankedHooks:
    """Note chaque variante puis classe par `overall` décroissant (tri stable)."""
    scored = [ScoredVariant(variant=v, score=predictor.score(v)) for v in variants]
    scored.sort(key=lambda s: s.score.overall, reverse=True)
    return RankedHooks(variants=scored)
