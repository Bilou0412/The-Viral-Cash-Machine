"""Dialoguiste FAKE — déterministe, hors-ligne (dev + tests).

Ignore le réseau : normalise chaque réplique (trim + majuscule initiale +
ponctuation finale) en gardant son id. Pas la puissance de reformulation du LLM,
mais un défaut offline propre et déterministe (mirror `FakeArtDirectionAgent`).
"""

from __future__ import annotations

from .model import Dialogue, DialogueLine, NarrationRef

_END = ".!?…"


def _polish(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    t = t[0].upper() + t[1:]
    if t[-1] not in _END:
        t += "."
    return t


class FakeDialogueAgent:
    """Implémente `DialogueAgent` sans appel réseau."""

    def write_dialogue(
        self,
        *,
        tone: str,
        audience: str,
        language: str,
        characters: dict[str, str],
        lines: list[NarrationRef],
    ) -> Dialogue:
        return Dialogue(
            lines=[
                DialogueLine(line_id=line.id, text=_polish(line.text))
                for line in lines
                if line.id
            ]
        )
