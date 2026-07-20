"""Systems service — sélectionne le décomposeur « Système expliqué » et le lance.

Miroir de `services/scenes.py` : clé OpenAI présente → impl OpenAI (VISION ; import
paresseux car le SDK est absent hors-ligne) ; sinon le Fake déterministe (offline/tests).
Applique le même filet de sécurité : aucun plan ne dépasse l'horizon i2v (5 s) — on scinde.
"""

from __future__ import annotations

import os

from ....features.assets.models import VIDEO_MODEL, max_coherent_duration_s
from ....features.scenes.model import VideoPlan
from ....features.scenes.split import split_overlong_shots
from ....features.systems.fake_system_explainer import FakeSystemExplainer
from ....features.systems.ports import DEFAULT_STEPS, SystemExplainer

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"  # doit accepter la VISION


def get_system_explainer(openai_key: str | None = None) -> SystemExplainer:
    """Renvoie l'impl OpenAI (vision) si une clé est donnée, sinon le Fake déterministe."""
    if not openai_key:
        return FakeSystemExplainer()
    # Import paresseux : le SDK `openai` est absent en offline/test.
    from openai import OpenAI

    from ....features.systems.openai_system_explainer import OpenAISystemExplainer

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAISystemExplainer(OpenAI(api_key=openai_key), model)


def generate_system_plan(
    image: str,
    *,
    hint: str = "",
    n_steps: int = DEFAULT_STEPS,
    language: str = "fr",
    platform: str = "tiktok",
    explainer: SystemExplainer | None = None,
    openai_key: str | None = None,
) -> VideoPlan:
    """Image → `VideoPlan` (système expliqué en plans courts) via le décomposeur choisi.

    Filet de sécurité : aucun plan ne dépasse l'horizon de cohérence du modèle vidéo
    (on scinde, on ne rabote pas) — le « 5 s max » est ainsi garanti de bout en bout.
    """
    exp = explainer or get_system_explainer(openai_key)
    plan = exp.explain_system(
        image, hint=hint, n_steps=n_steps, language=language, platform=platform
    )
    return split_overlong_shots(plan, max_coherent_s=max_coherent_duration_s(VIDEO_MODEL))
