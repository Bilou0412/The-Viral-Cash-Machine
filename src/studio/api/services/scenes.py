"""Scenes service — sélectionne le décrypteur de scènes et le lance.

Miroir de `scripting.get_decomposer`. Phase 1 : Fake déterministe (offline).
Phase 3 : clé OpenAI présente → impl OpenAI (import paresseux, SDK absent hors-ligne).
Le handler de route ignore la sélection.
"""

from __future__ import annotations

from ....features.scenes.fake_scene_decomposer import FakeSceneDecomposer
from ....features.scenes.model import VideoPlan
from ....features.scenes.ports import DEFAULT_SCENES, SceneVideoDecomposer


def get_scene_decomposer(openai_key: str | None = None) -> SceneVideoDecomposer:
    """Renvoie le décrypteur adapté. Phase 1 : toujours le Fake déterministe
    (l'impl OpenAI arrive en Phase 3, branchée sur ``openai_key``)."""
    return FakeSceneDecomposer()


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
