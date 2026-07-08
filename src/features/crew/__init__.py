"""Feature « crew » : le studio comme une équipe d'agents-métiers.

Chaque métier (scénariste, directeur artistique, chef op, dialoguiste, tournage,
monteur, ingé son, attaché de presse) est un agent. Le `roster` déclare l'équipe
par phase (pour l'UI « salle de production ») ; le premier agent dédié est
l'attaché de presse / Growth (`DistributionAgent` → `DistributionKit`).
"""

from .assemble import fragment_to_bricks
from .model import (
    ArtDirection,
    BeatPlan,
    Dialogue,
    DialogueLine,
    DistributionKit,
    FragmentPlan,
    NameplatePlan,
    NarrationRef,
    SceneArt,
    SceneRef,
)
from .ports import (
    ArtDirectionAgent,
    CrewAgentError,
    DialogueAgent,
    DirectorAgent,
    DistributionAgent,
)
from .roster import CREW, PHASES, CrewRole, role_by_key, roster

__all__ = [
    "CREW",
    "PHASES",
    "ArtDirection",
    "ArtDirectionAgent",
    "BeatPlan",
    "CrewAgentError",
    "CrewRole",
    "Dialogue",
    "DialogueAgent",
    "DialogueLine",
    "DirectorAgent",
    "DistributionAgent",
    "DistributionKit",
    "FragmentPlan",
    "NameplatePlan",
    "NarrationRef",
    "SceneArt",
    "SceneRef",
    "fragment_to_bricks",
    "role_by_key",
    "roster",
]
