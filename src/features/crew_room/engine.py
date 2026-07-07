"""Moteur de l'atelier — contrat → brouillons → mise en commun → révision informée.

Le réalisateur pose la scène à trous ; chaque département remplit SON brouillon
(à l'aveugle des autres) ; on assemble une scène PROVISOIRE ; puis chaque
département **voit l'ensemble** et ajuste SON champ pour la cohérence (révision),
et on réassemble. Déterministe. `revision_rounds=0` ⇒ pas de révision (comme avant).
"""

from __future__ import annotations

from ..brief.model import Brief
from ..scenes.model import ScenePlan
from .merge import contract_turn, draft_turns, merge_drafts
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
    revision_rounds: int = 1,
) -> RoomResult:
    """Crée une scène : contrat → brouillons (aveugles) → mise en commun → N tours
    de révision (chaque département voit la scène assemblée et ajuste ses champs).
    Renvoie la scène structurée + persos + transcript (les 2 passes visibles)."""
    contract = director.define(brief=brief, scene_brief=scene_brief, memory=memory)

    def _fill(dept: str) -> Draft:
        return drafters.fill(
            department=dept, contract=contract,
            brief=brief, scene_brief=scene_brief, memory=memory,
        )

    first: list[Draft] = [_fill(dept) for dept in departments]
    scene: ScenePlan = merge_drafts(scene_brief, contract, first).scene

    revised = first
    for _ in range(max(0, revision_rounds)):
        revised = [
            drafters.revise(
                department=dept, scene=scene, contract=contract,
                brief=brief, scene_brief=scene_brief, memory=memory,
            )
            for dept in departments
        ]
        scene = merge_drafts(scene_brief, contract, revised).scene

    result = merge_drafts(scene_brief, contract, revised)
    if revision_rounds > 0:
        result.transcript = [
            contract_turn(contract),
            *draft_turns(first, label="brouillon"),
            *draft_turns(revised, label="révision"),
        ]
    return result
