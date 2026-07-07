"""Ports de l'atelier — le RÉALISATEUR (pose le contrat) et les DÉPARTEMENTS
(remplissent leurs trous en parallèle).

Méthode : *contrat → brouillons parallèles → mise en commun*. Le réalisateur pose
la scène à trous (`SceneContract`) ; chaque département remplit un `Draft` limité
aux **champs qu'il possède** (`_FIELD_OWNER`), indépendamment ; l'assemblage
(`merge`) est mécanique car les champs sont disjoints.

Impls Fake (déterministe) et OpenAI (réel) injectées au bord. Réutilise
`CrewAgentError`.
"""

from __future__ import annotations

from typing import Protocol

from ..brief.model import Brief
from ..crew.ports import CrewAgentError
from ..scenes.model import ScenePlan
from .model import Draft, RoomMemory, SceneBrief, SceneContract

__all__ = ["DEPARTMENTS", "ContractAgent", "CrewAgentError", "Drafter", "field_owner"]

# Les départements qui remplissent la scène (dans l'ordre d'affichage). Le
# réalisateur, lui, POSE le contrat (il n'est pas un remplisseur).
DEPARTMENTS: tuple[str, ...] = (
    "directeur_artistique",
    "chef_operateur",
    "casting",
    "dialoguiste",
)

# Quel département POSSÈDE quel champ d'un plan (les trous disjoints).
_FIELD_OWNER: dict[str, str] = {
    "decor": "directeur_artistique",
    "lighting": "directeur_artistique",
    "framing": "chef_operateur",
    "duration": "chef_operateur",
    "narration": "dialoguiste",
    # `characters` est un champ à part (liste) → géré par le casting via `shot_characters`.
}


def field_owner(field: str) -> str:
    """Le département propriétaire d'un champ (vide si aucun)."""
    return _FIELD_OWNER.get(field, "")


class ContractAgent(Protocol):
    """Le réalisateur : pose la scène à trous (liste des plans + intentions)."""

    def define(
        self, *, brief: Brief, scene_brief: SceneBrief, memory: RoomMemory
    ) -> SceneContract:
        ...


class Drafter(Protocol):
    """Un département : remplit SON brouillon (ses champs), à l'aveugle (`fill`)
    puis, en voyant la scène assemblée, ajuste ses champs pour la cohérence (`revise`)."""

    def fill(
        self,
        *,
        department: str,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> Draft:
        ...

    def revise(
        self,
        *,
        department: str,
        scene: ScenePlan,
        contract: SceneContract,
        brief: Brief,
        scene_brief: SceneBrief,
        memory: RoomMemory,
    ) -> Draft:
        """2e passe : le département voit la scène ASSEMBLÉE (tous les champs) et
        ré-remplit SON brouillon pour la cohérence croisée. Mêmes champs que `fill`."""
        ...
