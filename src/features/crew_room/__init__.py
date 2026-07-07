"""Feature « crew_room » : la table ronde qui crée une scène par la discussion.

L'unité de création est la SCÈNE (créées en séquence, mémoire qui avance). Les
métiers-voix débattent en plusieurs tours, puis on synthétise la scène
structurée (format v4). Réutilise `features.scenes` (format) et `features.crew`
(erreurs) ; feature pure (aucune dépendance réseau au niveau module).
"""

from .engine import run_scene_room
from .fake_room import FakeRoomVoice, FakeSceneSynthesizer
from .model import RoomMemory, RoomResult, SceneBrief, Turn
from .ports import ROOM_VOICES, CrewAgentError, RoomVoice, SceneSynthesizer

__all__ = [
    "ROOM_VOICES",
    "CrewAgentError",
    "FakeRoomVoice",
    "FakeSceneSynthesizer",
    "RoomMemory",
    "RoomResult",
    "RoomVoice",
    "SceneBrief",
    "SceneSynthesizer",
    "Turn",
    "run_scene_room",
]
