"""Moteur de l'atelier — contrat → brouillons parallèles → mise en commun.

Le réalisateur pose la scène à trous ; chaque département remplit SON brouillon
(indépendamment, à l'aveugle des autres) ; on assemble. Déterministe. Les
brouillons ne dépendent pas les uns des autres → concurrence possible plus tard.
"""

from __future__ import annotations

from ..brief.model import Brief
from .merge import merge_drafts
from .model import Draft, RoomMemory, RoomResult, SceneBrief
from .ports import DEPARTMENTS, ContractAgent, Drafter


def run_scene_room(
    brief: Brief,
    scene_brief: SceneBrief,
    memory: RoomMemory,
    *,
    director: ContractAgent,
    drafters: Drafter,
    departments: tuple[str, ...] = DEPARTMENTS,
) -> RoomResult:
    """Crée une scène : le réalisateur pose le contrat, chaque département remplit
    ses trous, on met en commun. Renvoie la scène structurée + persos + transcript."""
    contract = director.define(brief=brief, scene_brief=scene_brief, memory=memory)
    drafts: list[Draft] = [
        drafters.fill(
            department=dept, contract=contract,
            brief=brief, scene_brief=scene_brief, memory=memory,
        )
        for dept in departments
    ]
    return merge_drafts(scene_brief, contract, drafts)
