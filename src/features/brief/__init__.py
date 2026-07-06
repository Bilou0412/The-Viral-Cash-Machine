"""Feature « brief » : le cahier des charges du producteur.

Première donnée de la chaîne — ce que le producteur veut (objectif, audience,
plateforme, durée, coût) — proposé par un agent producteur (dialogue/orientation)
puis édité. Alimente ensuite le décrypteur et les agents-métiers.
"""

from .fake_producer_agent import FakeProducerAgent
from .model import Brief, Platform
from .ports import CrewAgentError, ProducerAgent

__all__ = [
    "Brief",
    "CrewAgentError",
    "FakeProducerAgent",
    "Platform",
    "ProducerAgent",
]
