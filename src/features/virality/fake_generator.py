"""Générateur de hooks FAKE — déterministe, hors-ligne (dev + tests).

Ignore le réseau : décline une idée en N ouvertures sur des ANGLES distincts
(les archétypes qui marchent en short vertical). Sert de défaut offline et de golden.
"""

from __future__ import annotations

from .model import HookVariant
from .ports import DEFAULT_N_VARIANTS

# Angles d'ouverture par ordre de « punch » décroissant (archétypes short vertical).
_ANGLES: tuple[str, ...] = (
    "promesse choc",
    "in medias res",
    "compte à rebours",
    "question directe",
    "POV",
)


class FakeHookGenerator:
    """Implémente `HookVariantGenerator` sans appel réseau (angles déterministes)."""

    def generate_hooks(
        self,
        pitch: str,
        *,
        n: int = DEFAULT_N_VARIANTS,
        format_id: str = "scenes",
        language: str = "fr",
    ) -> list[HookVariant]:
        base = pitch.strip()
        count = max(1, n)
        out: list[HookVariant] = []
        for i in range(count):
            angle = _ANGLES[i % len(_ANGLES)]
            out.append(
                HookVariant(
                    id=f"hook{i + 1}",
                    angle=angle,
                    hook_text=f"{base[:60]} — ouverture « {angle} »".strip(" —"),
                    first_shot_prompt=(
                        f"vertical 9:16 opening frame, {angle} angle, of: {base[:80]}"
                    ),
                )
            )
        return out
