"""Port du décrypteur de scènes (à deux niveaux : vidéo→scènes, scène→plans).

Contrat unique : une idée (+ identité de style optionnelle) → un `VideoPlan`
complet. L'implémentation OpenAI (Phase 3) fera le découpage en deux phases ;
le Fake (offline/tests) renvoie un plan déterministe.
"""

from __future__ import annotations

from typing import Protocol

from .model import VideoPlan

DEFAULT_SCENES = 3


class SceneVideoDecomposer(Protocol):
    """Décrit une vidéo en scènes puis chaque scène en plans courts."""

    def decompose_video(
        self, prompt: str, *, style_identity: str = "", n_scenes: int = DEFAULT_SCENES
    ) -> VideoPlan:
        """Idée → `VideoPlan` (scènes + plans courts), respect strict de N scènes."""
        ...
