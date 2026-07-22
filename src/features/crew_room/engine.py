"""Moteur de l'atelier — la « boîte de prod » qui débat pour créer UNE scène.

Le réalisateur pose la scène à trous (contrat) ; chaque département remplit SON brouillon
**en parallèle** ; on assemble une scène provisoire. Puis, si un **superviseur** (`reviewer`)
est fourni, il relit la scène assemblée et **renvoie corriger les départements ciblés** — en
boucle (max `max_rounds`) — jusqu'à validation : c'est lui qui orchestre les protagonistes.

Sans `reviewer` : comportement **legacy** (révision fixe de tous les départements sur
`revision_rounds` tours) — conservé pour la rétro-compat. Déterministe côté Fake.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from ..brief.model import Brief
from ..scenes.model import ScenePlan
from .merge import contract_turn, draft_turns, merge_drafts
from .model import (
    Draft,
    ReviewVerdict,
    RoomMemory,
    RoomResult,
    SceneBrief,
    SceneContract,
    Turn,
)
from .ports import DEPARTMENTS, ContractAgent, Drafter, Reviewer


def _parallel(fn: Callable[[str], Draft], depts: list[str]) -> list[Draft]:
    """Exécute `fn` sur chaque département EN PARALLÈLE (les appels LLM sont I/O-bound :
    les threads donnent une vraie concurrence, et réduisent la surface d'échec séquentiel).
    Ordre d'entrée préservé."""
    if not depts:
        return []
    with ThreadPoolExecutor(max_workers=len(depts)) as ex:
        return list(ex.map(fn, depts))


def _fill_all(
    drafters: Drafter, depts: list[str], contract: SceneContract,
    brief: Brief, scene_brief: SceneBrief, memory: RoomMemory,
) -> list[Draft]:
    def _one(dept: str) -> Draft:
        return drafters.fill(
            department=dept, contract=contract,
            brief=brief, scene_brief=scene_brief, memory=memory,
        )
    return _parallel(_one, depts)


def _revise_all(
    drafters: Drafter, depts: list[str], scene: ScenePlan, contract: SceneContract,
    brief: Brief, scene_brief: SceneBrief, memory: RoomMemory, notes: dict[str, str],
) -> list[Draft]:
    def _one(dept: str) -> Draft:
        return drafters.revise(
            department=dept, scene=scene, contract=contract,
            brief=brief, scene_brief=scene_brief, memory=memory, note=notes.get(dept, ""),
        )
    return _parallel(_one, depts)


def _verdict_turn(verdict: ReviewVerdict) -> Turn:
    """Le verdict du superviseur, rendu comme un tour de débat (rôle réalisateur)."""
    if verdict.ok and not verdict.redo:
        return Turn(role="realisateur", message=f"✅ {verdict.note or 'Scène validée.'}")
    todo = "; ".join(f"{d} → {note}" for d, note in verdict.redo.items())
    return Turn(role="realisateur", message=f"↩ {verdict.note or 'À retravailler'} ({todo})")


def run_scene_room(
    brief: Brief,
    scene_brief: SceneBrief,
    memory: RoomMemory,
    *,
    director: ContractAgent,
    drafters: Drafter,
    reviewer: Reviewer | None = None,
    departments: tuple[str, ...] = DEPARTMENTS,
    revision_rounds: int = 1,
    max_rounds: int = 2,
) -> RoomResult:
    """Crée une scène : contrat → brouillons PARALLÈLES → mise en commun → révision.

    Avec `reviewer` : boucle de révision **ciblée** pilotée par le superviseur (la boîte
    de prod qui débat). Sans : `revision_rounds` tours de révision de TOUS les départements
    (legacy). Renvoie la scène structurée + persos + le transcript du débat."""
    depts = list(departments)
    contract = director.define(brief=brief, scene_brief=scene_brief, memory=memory)

    first = _fill_all(drafters, depts, contract, brief, scene_brief, memory)
    by_dept: dict[str, Draft] = dict(zip(depts, first, strict=True))
    scene: ScenePlan = merge_drafts(scene_brief, contract, list(by_dept.values())).scene
    turns: list[Turn] = [contract_turn(contract), *draft_turns(first, label="brouillon")]

    if reviewer is None:
        # LEGACY : révision fixe de TOUS les départements (rétro-compat, transcript inchangé).
        revised = first
        for _ in range(max(0, revision_rounds)):
            revised = _revise_all(drafters, depts, scene, contract, brief, scene_brief, memory, {})
            scene = merge_drafts(scene_brief, contract, revised).scene
        result = merge_drafts(scene_brief, contract, revised)
        if revision_rounds > 0:
            turns += draft_turns(revised, label="révision")
        result.transcript = turns
        return result

    # SUPERVISEUR : le réalisateur relit et renvoie corriger les départements ciblés, en boucle.
    for _ in range(max(0, max_rounds)):
        verdict = reviewer.review(
            scene=scene, contract=contract, brief=brief, scene_brief=scene_brief, memory=memory
        )
        turns.append(_verdict_turn(verdict))
        todo = [d for d in depts if d in verdict.redo]
        if verdict.ok or not todo:
            break
        redone = _revise_all(drafters, todo, scene, contract, brief, scene_brief, memory, verdict.redo)
        by_dept.update(dict(zip(todo, redone, strict=True)))
        scene = merge_drafts(scene_brief, contract, list(by_dept.values())).scene
        turns += draft_turns(redone, label="révision")

    result = merge_drafts(scene_brief, contract, list(by_dept.values()))
    result.transcript = turns
    return result
