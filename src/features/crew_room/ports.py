"""Ports de la table ronde — les VOIX et le SYNTHÉTISEUR.

Une **voix** (`RoomVoice`) parle au nom d'un métier en voyant le brief, le
squelette de scène, la mémoire et le débat en cours. Le **synthétiseur**
(`SceneSynthesizer`) lit le débat et en extrait la scène structurée.

Impls Fake (déterministe, hors-ligne) et OpenAI (réel) injectées au bord.
Réutilise `CrewAgentError`.
"""

from __future__ import annotations

from typing import Protocol

from ..brief.model import Brief
from ..crew.ports import CrewAgentError
from .model import RoomMemory, RoomResult, SceneBrief, Turn

__all__ = ["ROOM_VOICES", "CrewAgentError", "RoomVoice", "SceneSynthesizer"]

# Les métiers présents à la table ronde d'une scène, DANS L'ORDRE de parole
# (le réalisateur cadre en premier, puis les départements). Clés = `CrewRole.key`.
ROOM_VOICES: tuple[str, ...] = (
    "realisateur",
    "directeur_artistique",
    "chef_operateur",
    "casting",
    "dialoguiste",
)


class RoomVoice(Protocol):
    """Une voix de la table ronde : le prochain message d'un métier."""

    def speak(
        self,
        *,
        role: str,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
        transcript: list[Turn],
    ) -> str:
        """Ce que dit `role` maintenant, au vu du débat et du contexte."""
        ...


class SceneSynthesizer(Protocol):
    """Extrait du débat la scène STRUCTURÉE (format v4) + les persos neufs."""

    def synthesize(
        self, *, brief: Brief, scene_brief: SceneBrief, memory: RoomMemory, transcript: list[Turn]
    ) -> RoomResult:
        ...
