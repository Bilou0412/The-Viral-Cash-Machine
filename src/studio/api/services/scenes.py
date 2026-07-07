"""Scenes service — sélectionne le décrypteur de scènes et le lance.

Miroir de `scripting.get_decomposer` : clé OpenAI présente → impl OpenAI (deux
phases ; import paresseux car le SDK est absent hors-ligne) ; sinon le Fake
déterministe (offline/tests). Le handler de route ignore la sélection.
"""

from __future__ import annotations

import os
from typing import Literal

from ....features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from ....features.scenes.model import ScenePlan, VideoPlan
from ....features.scenes.ports import DEFAULT_SCENES, SceneVideoDecomposer

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

DecomposerSource = Literal["openai", "fake"]


def decomposer_source(openai_key: str | None) -> DecomposerSource:
    """Quel décrypteur sera utilisé (sans instancier OpenAI) : réel si clé présente,
    sinon le Fake déterministe. Sert à avertir l'utilisateur qu'il génère des scènes
    de démo (placeholder) tant qu'aucune clé OpenAI n'est configurée."""
    return "openai" if openai_key else "fake"


def get_scene_decomposer(openai_key: str | None = None) -> SceneVideoDecomposer:
    """Renvoie l'impl OpenAI si une clé est donnée, sinon le Fake déterministe."""
    if not openai_key:
        return FakeSceneDecomposer()
    # Import paresseux : le SDK `openai` est absent en offline/test.
    from openai import OpenAI

    from ....features.scenes.openai_scene_decomposer import OpenAISceneDecomposer

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAISceneDecomposer(OpenAI(api_key=openai_key), model)


def generate_arc(
    prompt: str,
    *,
    style_identity: str = "",
    n_scenes: int = DEFAULT_SCENES,
    platform: str = "tiktok",
    language: str = "fr",
    decomposer: SceneVideoDecomposer | None = None,
    openai_key: str | None = None,
) -> list[ScenePlan]:
    """Idée → l'ARC (squelettes de scènes ordonnés, sans plans) via le décrypteur."""
    dec = decomposer or get_scene_decomposer(openai_key)
    return dec.plan_arc(
        prompt, style_identity=style_identity, n_scenes=n_scenes,
        platform=platform, language=language,
    )


def generate_video_plan(
    prompt: str,
    *,
    style_identity: str = "",
    n_scenes: int = DEFAULT_SCENES,
    platform: str = "tiktok",
    language: str = "fr",
    target_duration_s: float = 0.0,
    decomposer: SceneVideoDecomposer | None = None,
    openai_key: str | None = None,
) -> VideoPlan:
    """Idée → `VideoPlan` (scènes + plans courts) via le décrypteur choisi.

    Les paramètres `platform`/`language`/`target_duration_s` viennent du Brief du
    producteur (défauts = comportement historique). Le ton/notes du Brief sont
    repliés dans `style_identity` par l'appelant (seam existant)."""
    dec = decomposer or get_scene_decomposer(openai_key)
    return dec.decompose_video(
        prompt,
        style_identity=style_identity,
        n_scenes=n_scenes,
        platform=platform,
        language=language,
        target_duration_s=target_duration_s,
    )
