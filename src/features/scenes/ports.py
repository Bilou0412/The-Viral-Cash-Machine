"""Port du décrypteur de scènes (à deux niveaux : vidéo→scènes, scène→plans).

Contrat unique : une idée (+ identité de style optionnelle) → un `VideoPlan`
complet. L'implémentation OpenAI (Phase 3) fera le découpage en deux phases ;
le Fake (offline/tests) renvoie un plan déterministe.
"""

from __future__ import annotations

from typing import Protocol

from .model import ScenePlan, VideoPlan

DEFAULT_SCENES = 3


class SceneDecompositionError(ValueError):
    """L'IA n'a pas pu produire un découpage exploitable (réponse vide/illisible).

    Levée quand aucune scène n'est extraite du plan macro : mieux vaut une erreur
    claire remontée à l'utilisateur qu'une vidéo vide générée silencieusement.
    """


class SceneVideoDecomposer(Protocol):
    """Décrit une vidéo en scènes puis chaque scène en plans courts."""

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
        """Idée → `VideoPlan` (scènes + plans courts), respect strict de N scènes.

        `platform`/`language`/`target_duration_s` viennent du Brief du producteur
        (défauts = comportement historique). `style_identity` porte le ton/notes.
        """
        ...

    def plan_arc(
        self,
        prompt: str,
        *,
        style_identity: str = "",
        n_scenes: int = DEFAULT_SCENES,
        platform: str = "tiktok",
        language: str = "fr",
    ) -> list[ScenePlan]:
        """MACRO seul : l'ARC = les squelettes de scènes ordonnés (sans plans).

        Chaque `ScenePlan` porte id/title/environment_desc/context_text ; les
        plans (`shots`) sont laissés vides — c'est la table ronde qui les crée.
        """
        ...
