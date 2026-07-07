"""Virality service — génère N hooks, les note, les classe (un seul appel).

Miroir de `scenes.get_scene_decomposer` : clé OpenAI présente → impls OpenAI (import
paresseux) ; sinon les Fakes déterministes (offline/tests). Le handler de route ignore
la sélection. C'est la brique « 3 variantes → prédiction » de l'endgame.
"""

from __future__ import annotations

import os
from typing import Literal

from ....features.virality import (
    DEFAULT_N_VARIANTS,
    FakeHookGenerator,
    FakeViralityPredictor,
    HookVariantGenerator,
    RankedHooks,
    ViralityError,
    ViralityPredictor,
    rank_hooks,
)

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

ViralitySource = Literal["openai", "fake"]


def virality_source(openai_key: str | None) -> ViralitySource:
    """Quel moteur (sans instancier OpenAI) : réel si clé, sinon Fake déterministe."""
    return "openai" if openai_key else "fake"


def get_hook_generator(openai_key: str | None = None) -> HookVariantGenerator:
    """Générateur de hooks : OpenAI si clé, sinon Fake déterministe."""
    if not openai_key:
        return FakeHookGenerator()
    from openai import OpenAI

    from ....features.virality.openai_generator import OpenAIHookGenerator

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIHookGenerator(OpenAI(api_key=openai_key), model)


def get_virality_predictor(openai_key: str | None = None) -> ViralityPredictor:
    """Prédicteur de viralité : OpenAI (LLM-juge) si clé, sinon Fake déterministe."""
    if not openai_key:
        return FakeViralityPredictor()
    from openai import OpenAI

    from ....features.virality.openai_predictor import OpenAIViralityPredictor

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIViralityPredictor(OpenAI(api_key=openai_key), model)


def propose_hooks(
    pitch: str,
    *,
    n_variants: int = DEFAULT_N_VARIANTS,
    format_id: str = "scenes",
    language: str = "fr",
    openai_key: str | None = None,
    generator: HookVariantGenerator | None = None,
    predictor: ViralityPredictor | None = None,
) -> RankedHooks:
    """Idée → N variantes de hook, notées et CLASSÉES (la 1re = la gagnante).

    Le générateur et le prédicteur sont injectables (ports) — tests offline via Fakes.
    """
    gen = generator or get_hook_generator(openai_key)
    pred = predictor or get_virality_predictor(openai_key)
    variants = gen.generate_hooks(
        pitch, n=n_variants, format_id=format_id, language=language
    )
    if not variants:
        raise ViralityError("Aucune variante de hook générée ; reformule l'idée.")
    return rank_hooks(variants, pred)
