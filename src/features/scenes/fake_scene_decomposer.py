"""Décrypteur de scènes FAKE — déterministe, hors-ligne (dev + tests).

Ignore le contenu du prompt (pas de réseau) : produit `n_scenes` scènes, chacune
avec une photo d'environnement + 2 plans courts (3-4 s) et de la narration. Sert
de défaut offline et de golden du chemin scènes (mirror `FakeAdventureDecomposer`).
"""

from __future__ import annotations

from .model import CharacterPlan, ScenePlan, ShotCharacterPlan, ShotPlan, VideoPlan
from .ports import DEFAULT_SCENES

# Un personnage récurrent de démo (la bible) — déterministe.
_HERO = CharacterPlan(
    name="Léa",
    appearance="young woman, short dark hair",
    wardrobe="worn grey coat",
    voice_id="Deep_Voice_Man",
    traits="determined, wary",
)


class FakeSceneDecomposer:
    """Implémente `SceneVideoDecomposer` sans appel réseau.

    v4 : émet des CHAMPS MÉTIER structurés (décor / cadrage / personnages) — pas
    seulement un blob — pour que la démo offline montre la décomposition.
    """

    def decompose_video(
        self,
        prompt: str,
        *,
        style_identity: str = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
        target_duration_s: float = 0.0,
    ) -> VideoPlan:
        # Déterministe/offline : les paramètres du Brief sont acceptés puis ignorés.
        scenes: list[ScenePlan] = []
        for i in range(max(1, n_scenes)):
            n = i + 1
            scenes.append(
                ScenePlan(
                    id=f"s{n}",
                    title=f"Scène {n}",
                    environment_desc=f"wide establishing shot of location {n}, cinematic",
                    lighting="cold ambient light",
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
                            decor=f"location {n} interior",
                            lighting="cold ambient light",
                            framing="close-up",
                            characters=[
                                ShotCharacterPlan(name="Léa", expression="tense", action="looking around")
                            ],
                        ),
                        ShotPlan(
                            id=f"s{n}_sh2",
                            kind="video",
                            visual_desc=f"POV reaction inside location {n}",
                            motion_desc="handheld, static framing",
                            narration_fr="Un choix s'impose.",
                            duration_s=4.0,
                            decor=f"location {n} interior",
                            lighting="cold ambient light",
                            framing="medium POV shot",
                            characters=[
                                ShotCharacterPlan(name="Léa", expression="resolute", action="deciding")
                            ],
                        ),
                    ],
                )
            )
        return VideoPlan(
            title="Vidéo générée",
            global_context=prompt or "une courte vidéo verticale",
            cast=[_HERO],
            art_direction="cold tones",
            scenes=scenes,
        )

    def plan_arc(
        self,
        prompt: str,
        *,
        style_identity: str = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
    ) -> list[ScenePlan]:
        # Squelettes déterministes (sans plans) — la table ronde les remplira.
        beats = ["Accroche", "Montée", "Chute"]
        return [
            ScenePlan(
                id=f"s{i + 1}",
                title=f"Scène {i + 1} — {beats[i] if i < len(beats) else 'Suite'}",
                environment_desc=f"establishing shot of location {i + 1}, cinematic",
                context_text=f"Le contexte concentré de la scène {i + 1}.",
            )
            for i in range(max(1, n_scenes))
        ]
