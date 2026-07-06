"""Attaché de presse FAKE — déterministe, hors-ligne (dev + tests).

Ignore le réseau : dérive un kit de distribution plausible du titre/synopsis.
Sert de défaut offline et de golden (mirror `FakeSceneDecomposer`).
"""

from __future__ import annotations

from .model import DistributionKit


class FakeDistributionAgent:
    """Implémente `DistributionAgent` sans appel réseau."""

    def write_kit(
        self, *, title: str, synopsis: str, narration: str = ""
    ) -> DistributionKit:
        name = title.strip() or "Nouvelle vidéo"
        return DistributionKit(
            title=f"{name} 😱 (tu ne vas pas y croire)",
            description=(
                f"{synopsis.strip() or name} — une vidéo verticale à regarder "
                "jusqu'au bout. Abonne-toi pour la suite !"
            ),
            hashtags=["#fyp", "#pourtoi", "#story", "#viral", "#shorts"],
            hook=narration.strip() or "Attends de voir la fin…",
        )
