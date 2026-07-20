"""Port du décomposeur « Système expliqué ».

Contrat unique : une IMAGE (+ indice texte optionnel) → un `VideoPlan` complet qui
EXPLIQUE le système montré, en plans courts (≤ horizon i2v). L'impl OpenAI utilise la
VISION (décrire l'image puis dérouler les étapes) ; le Fake (offline/tests) renvoie un
plan déterministe. On réutilise le modèle `VideoPlan` des scènes — même IR, même rail.
"""

from __future__ import annotations

from typing import Protocol

from ..scenes.model import VideoPlan

DEFAULT_STEPS = 4


class SystemExplainError(ValueError):
    """L'IA n'a pas pu produire une explication exploitable (image illisible/réponse vide).

    Mieux vaut une erreur claire remontée à l'utilisateur qu'une vidéo vide générée
    silencieusement quand l'analyse de l'image échoue.
    """


class SystemExplainer(Protocol):
    """Analyse une image de système et l'explique en une suite de plans courts."""

    def explain_system(
        self,
        image: str,
        *,
        hint: str = "",
        n_steps: int = DEFAULT_STEPS,
        language: str = "fr",
        platform: str = "tiktok",
    ) -> VideoPlan:
        """Image → `VideoPlan` : le système identifié + N étapes expliquées (plans courts).

        `image` : URL, data-URI ou chemin de l'image d'entrée (1er argument du format).
        `hint` : précision texte optionnelle (« explique la construction », « le circuit »…).
        `n_steps` : nombre d'étapes voulues (chaque étape = une scène + un plan court).
        `language` : langue de la narration (FR par défaut) ; les prompts visuels restent EN.
        """
        ...
