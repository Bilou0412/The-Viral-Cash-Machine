"""Scenes service — sélectionne le décrypteur de scènes et le lance.

Miroir de `scripting.get_decomposer` : clé OpenAI présente → impl OpenAI (deux
phases ; import paresseux car le SDK est absent hors-ligne) ; sinon le Fake
déterministe (offline/tests). Le handler de route ignore la sélection.
"""

from __future__ import annotations

import os

from ....features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from ....features.scenes.model import VideoPlan
from ....features.scenes.ports import DEFAULT_SCENES, SceneVideoDecomposer

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


def get_scene_decomposer(openai_key: str | None = None) -> SceneVideoDecomposer:
    """Renvoie l'impl OpenAI si une clé est donnée, sinon le Fake déterministe."""
    if not openai_key:
        return FakeSceneDecomposer()
    # Import paresseux : le SDK `openai` est absent en offline/test.
    from openai import OpenAI

    from ....features.scenes.openai_scene_decomposer import OpenAISceneDecomposer

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAISceneDecomposer(OpenAI(api_key=openai_key), model)


def generate_video_plan(
    prompt: str,
    *,
    style_identity: str = "",
    n_scenes: int = DEFAULT_SCENES,
    decomposer: SceneVideoDecomposer | None = None,
    openai_key: str | None = None,
) -> VideoPlan:
    """Idée → `VideoPlan` (scènes + plans courts) via le décrypteur choisi."""
    dec = decomposer or get_scene_decomposer(openai_key)
    return dec.decompose_video(prompt, style_identity=style_identity, n_scenes=n_scenes)
