"""Directeur artistique FAKE — déterministe, hors-ligne (dev + tests).

Ignore le réseau : pose une art direction dérivée du ton/plateforme et enrichit
le prompt image de chaque scène d'un suffixe de style cohérent (en gardant le
décor). Sert de défaut offline et de golden (mirror `FakeDistributionAgent`).
"""

from __future__ import annotations

from .model import ArtDirection, SceneArt, SceneRef


def _style_line(tone: str) -> str:
    """Une ligne d'art direction déterministe dérivée du ton."""
    base = tone.strip() or "cinematic, cohesive mood"
    return f"{base}, consistent color grade, cohesive lighting, filmic texture"


class FakeArtDirectionAgent:
    """Implémente `ArtDirectionAgent` sans appel réseau."""

    def direct(
        self,
        *,
        tone: str,
        platform: str,
        language: str,
        art_direction: str,
        scenes: list[SceneRef],
    ) -> ArtDirection:
        style = _style_line(tone)
        suffix = f"— art direction: {style}"
        rewritten = [
            SceneArt(
                scene_id=s.id,
                # On garde le décor et on lui applique le style commun (EN).
                environment_prompt=f"{s.environment.strip()} {suffix}".strip(),
            )
            for s in scenes
        ]
        return ArtDirection(art_direction=style, scenes=rewritten)
