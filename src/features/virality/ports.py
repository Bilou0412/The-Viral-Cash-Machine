"""Ports de la boucle VIRALITÉ (`typing.Protocol`) — dépendre du contrat, pas de l'impl.

Deux rôles, injectés au bord (Fake offline / OpenAI réel) :
- `HookVariantGenerator` : idée → N variantes d'ouverture ;
- `ViralityPredictor` : une variante → sa viralité prédite.
"""

from __future__ import annotations

from typing import Protocol

from .model import HookVariant, ViralityScore

DEFAULT_N_VARIANTS = 3


class ViralityError(RuntimeError):
    """Échec de génération/prédiction (LLM injoignable, sortie illisible…)."""


class HookVariantGenerator(Protocol):
    """Produit N ouvertures CONCURRENTES pour une même idée (angles distincts)."""

    def generate_hooks(
        self,
        pitch: str,
        *,
        n: int = DEFAULT_N_VARIANTS,
        format_id: str = "scenes",
        language: str = "fr",
    ) -> list[HookVariant]: ...


class ViralityPredictor(Protocol):
    """Note la viralité prédite d'une variante (0..100 + décomposition)."""

    def score(self, variant: HookVariant) -> ViralityScore: ...
