"""Port du producteur — l'agent de dialogue qui pose/oriente le Brief.

Le producteur est **plus un agent de dialogue qu'un formulaire** : à partir d'une
idée brute (+ d'éventuelles réponses partielles), il **propose un Brief complété**
que le producteur humain édite ensuite. Impls Fake (déterministe) et OpenAI
(réel) injectées au bord (mirror du décrypteur / de l'attaché de presse).

`CrewAgentError` est réutilisé (pas réinventé) : c'est la même sémantique « un
agent-métier n'a pas pu produire un artefact exploitable ».
"""

from __future__ import annotations

from typing import Protocol

from ..crew.ports import CrewAgentError
from .model import Brief

__all__ = ["CrewAgentError", "ProducerAgent"]


class ProducerAgent(Protocol):
    """Le producteur : idée (+ réponses partielles) → Brief structuré complété."""

    def draft_brief(self, *, idea: str, partial: Brief | None = None) -> Brief:
        """Idée brute → `Brief` complété/orienté.

        `partial` = les champs déjà décidés par le producteur humain ; l'agent
        complète les trous sans écraser ce qui est fourni (l'humain garde la main).
        """
        ...
