"""Décomposeur « Système expliqué » FAKE — déterministe, hors-ligne (dev + tests).

N'ouvre jamais l'image (pas d'I/O, pas de réseau) : produit un `VideoPlan` déterministe
qui EXPLIQUE un système générique en N étapes. Chaque étape = une SCÈNE (photo du système)
+ un PLAN court (≤ horizon) avec narration FR et sujet visuel EN. Sert de défaut offline,
de golden, et instancie le template pour l'aperçu.
"""

from __future__ import annotations

from ...editor.document import Cadre, Camera, IntentionGlobale, RenderMeta
from ..scenes.model import ScenePlan, ShotPlan, VideoPlan
from .ports import DEFAULT_STEPS

_META = RenderMeta(
    ratio="9:16",
    fps=30,
    resolution="1080p",
    style_rendu="clean explanatory 3D, soft studio light",
    grain_etalonnage="neutral, high clarity",
)

# Squelette d'explication générique (indépendant de l'image, pour l'offline).
_STEPS = (
    ("On identifie le système et ses grandes parties.",
     "labeled overview of the whole system, exploded diagram, neutral background"),
    ("On regarde les fondations, la base qui porte tout.",
     "close-up on the base / foundation layer of the system, cutaway view"),
    ("On assemble les éléments principaux, un par un.",
     "main components being placed and connected step by step, animated assembly"),
    ("On voit comment les parties interagissent en fonctionnement.",
     "system running, flows and connections highlighted with arrows"),
    ("On termine par le résultat final, complet et opérationnel.",
     "finished complete system, clean hero shot, subtle rotation"),
)


def _step_scene(i: int, narration: str, visual: str) -> ScenePlan:
    """Une étape = une scène (photo du système) + un plan court qui l'anime."""
    return ScenePlan(
        id=f"step{i}",
        title=f"Étape {i}",
        environment_desc=f"clean explanatory shot of the system, step {i}: {visual}",
        location_ref="systeme",
        mood="clear, instructive",
        intention_scene=f"expliquer l'étape {i} du système",
        shots=[
            ShotPlan(
                id=f"step{i}_sh1",
                kind="video",
                duree_s=4.0,  # ≤ horizon (5 s) — pas de split nécessaire
                narration_fr=narration,
                start_image=visual,
                sujet=visual,
                cadre=Cadre(taille_plan="medium shot", focale="50mm", angle_hauteur="eye level"),
                camera=Camera(type="slow push in", vitesse="slow", depart_arrivee="from wide to detail"),
                intention_plan=f"montrer l'étape {i}",
            )
        ],
    )


class FakeSystemExplainer:
    """Implémente `SystemExplainer` sans appel réseau (explication déterministe)."""

    def explain_system(
        self,
        image: str,
        *,
        hint: str = "",
        n_steps: int = DEFAULT_STEPS,
        language: str = "fr",
        platform: str = "tiktok",
    ) -> VideoPlan:
        # Déterministe/offline : l'image et les paramètres sont acceptés puis ignorés.
        count = max(1, n_steps)
        steps = [_STEPS[i % len(_STEPS)] for i in range(count)]
        return VideoPlan(
            title=hint.strip() or "Système expliqué",
            meta=_META,
            intention_globale=IntentionGlobale(
                genre="explainer court",
                ton="pédagogique, clair",
                arc_narratif=hint or "expliquer comment fonctionne le système montré, étape par étape",
            ),
            musique_score="light curious background, steady tempo",
            scenes=[_step_scene(i + 1, narration, visual) for i, (narration, visual) in enumerate(steps)],
        )
