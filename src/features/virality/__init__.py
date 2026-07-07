"""Feature VIRALITÉ — la boucle « N variantes de hook → prédiction → classement ».

Ports (`HookVariantGenerator`, `ViralityPredictor`) + impls Fake (offline) / OpenAI
(réel) + classement pur (`rank_hooks`). Import-light : `openai` reste paresseux."""

from .fake_generator import FakeHookGenerator
from .fake_predictor import FakeViralityPredictor
from .model import HookVariant, RankedHooks, ScoredVariant, ViralityScore
from .ports import (
    DEFAULT_N_VARIANTS,
    HookVariantGenerator,
    ViralityError,
    ViralityPredictor,
)
from .select import rank_hooks

__all__ = [
    "DEFAULT_N_VARIANTS",
    "FakeHookGenerator",
    "FakeViralityPredictor",
    "HookVariant",
    "HookVariantGenerator",
    "RankedHooks",
    "ScoredVariant",
    "ViralityError",
    "ViralityPredictor",
    "ViralityScore",
    "rank_hooks",
]
