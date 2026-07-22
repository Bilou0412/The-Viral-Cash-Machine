"""Feature « crew_room » : l'atelier qui crée une scène.

Méthode *contrat → brouillons parallèles → mise en commun* (inspirée d'un harnais
d'agents) : le réalisateur pose la scène À TROUS, chaque département remplit SES
trous indépendamment, on assemble (champs disjoints → merge mécanique). Réutilise
`features.scenes` (format v4) et `features.crew` (erreurs) ; feature pure.
"""

from .engine import run_scene_room
from .fake_room import FakeContractAgent, FakeDrafter, FakeReviewer
from .merge import merge_drafts
from .model import (
    ContractShot,
    Draft,
    ReviewVerdict,
    RoomMemory,
    RoomResult,
    SceneBrief,
    SceneContract,
    Turn,
)
from .ports import DEPARTMENTS, ContractAgent, CrewAgentError, Drafter, Reviewer

__all__ = [
    "DEPARTMENTS",
    "ContractAgent",
    "ContractShot",
    "CrewAgentError",
    "Draft",
    "Drafter",
    "FakeContractAgent",
    "FakeDrafter",
    "FakeReviewer",
    "ReviewVerdict",
    "Reviewer",
    "RoomMemory",
    "RoomResult",
    "SceneBrief",
    "SceneContract",
    "Turn",
    "merge_drafts",
    "run_scene_room",
]
