"""Feature « crew » : le studio comme une équipe d'agents-métiers.

Chaque métier (scénariste, directeur artistique, chef op, dialoguiste, tournage,
monteur, ingé son, attaché de presse) est un agent. Le `roster` déclare l'équipe
par phase (pour l'UI « salle de production ») ; le premier agent dédié est
l'attaché de presse / Growth (`DistributionAgent` → `DistributionKit`).
"""

from .model import DistributionKit
from .ports import CrewAgentError, DistributionAgent
from .roster import CREW, PHASES, CrewRole, roster

__all__ = [
    "CREW",
    "PHASES",
    "CrewAgentError",
    "CrewRole",
    "DistributionAgent",
    "DistributionKit",
    "roster",
]
