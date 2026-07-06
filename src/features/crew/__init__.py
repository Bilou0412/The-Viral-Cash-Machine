"""Feature « crew » : le studio comme une équipe d'agents-métiers.

Chaque métier (scénariste, directeur artistique, chef op, dialoguiste, tournage,
monteur, ingé son, attaché de presse) est un agent. Le `roster` déclare l'équipe
par phase (pour l'UI « salle de production ») ; le premier agent dédié est
l'attaché de presse / Growth (`DistributionAgent` → `DistributionKit`).
"""

from .model import (
    ArtDirection,
    Dialogue,
    DialogueLine,
    DistributionKit,
    NarrationRef,
    SceneArt,
    SceneRef,
)
from .ports import (
    ArtDirectionAgent,
    CrewAgentError,
    DialogueAgent,
    DistributionAgent,
)
from .roster import CREW, PHASES, CrewRole, role_by_key, roster

__all__ = [
    "CREW",
    "PHASES",
    "ArtDirection",
    "ArtDirectionAgent",
    "CrewAgentError",
    "CrewRole",
    "Dialogue",
    "DialogueAgent",
    "DialogueLine",
    "DistributionAgent",
    "DistributionKit",
    "NarrationRef",
    "SceneArt",
    "SceneRef",
    "role_by_key",
    "roster",
]
