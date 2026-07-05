"""Décrypteur de scènes FAKE — déterministe, hors-ligne (dev + tests).

Ignore le contenu du prompt (pas de réseau) : produit `n_scenes` scènes, chacune
avec une photo d'environnement + 2 plans courts (3-4 s) et de la narration. Sert
de défaut offline et de golden du chemin scènes (mirror `FakeAdventureDecomposer`).
"""

from __future__ import annotations

from .model import ScenePlan, ShotPlan, VideoPlan
from .ports import DEFAULT_SCENES


class FakeSceneDecomposer:
    """Implémente `SceneVideoDecomposer` sans appel réseau."""

    def decompose_video(
        self, prompt: str, *, style_identity: str = "", n_scenes: int = DEFAULT_SCENES
    ) -> VideoPlan:
        scenes: list[ScenePlan] = []
        for i in range(max(1, n_scenes)):
            n = i + 1
            scenes.append(
                ScenePlan(
                    id=f"s{n}",
                    title=f"Scène {n}",
                    environment_desc=(
                        f"wide establishing shot of location {n}, cinematic, cold tones"
                    ),
                    context_text=f"Le contexte concentré de la scène {n}.",
                    art_direction="cold tones, film grain",
                    shots=[
                        ShotPlan(
                            id=f"s{n}_sh1",
                            kind="video",
                            visual_desc=f"detail shot inside location {n}",
                            motion_desc="slow push in, static camera",
                            narration_fr="La tension monte.",
                            duration_s=3.0,
                        ),
                        ShotPlan(
                            id=f"s{n}_sh2",
                            kind="video",
                            visual_desc=f"POV reaction inside location {n}",
                            motion_desc="handheld, static framing",
                            narration_fr="Un choix s'impose.",
                            duration_s=4.0,
                        ),
                    ],
                )
            )
        return VideoPlan(
            title="Vidéo générée",
            global_context=prompt or "une courte vidéo verticale",
            art_direction="cold tones",
            scenes=scenes,
        )
