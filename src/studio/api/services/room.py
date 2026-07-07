"""Orchestration séquentielle de la table ronde — scène par scène, avec mémoire.

L'arc (macro, le scénariste) donne les scènes ordonnées. Puis, pour chaque scène
dans l'ordre, la **table ronde** la crée en discutant, et la **mémoire avance**
(bible cumulée + synopsis). L'état (arc + mémoire + transcrits + scènes faites)
est persisté hors du doc (colonne `memory_json`) ; les scènes atterrissent dans
l'`EditorDocument` via `append_scene` (format v4, génération inchangée).

Sélection Fake/OpenAI par présence de clé (miroir des autres services).
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

from ....editor.document import EditorDocument
from ....features.brief.model import Brief
from ....features.crew_room import (
    ContractAgent,
    Drafter,
    FakeContractAgent,
    FakeDrafter,
    RoomMemory,
    SceneBrief,
    Turn,
    run_scene_room,
)
from ....features.scenes import ScenePlan, append_scene
from .crew import DEFAULT_OPENAI_MODEL, AgentSource, agent_source

__all__ = [
    "AgentSource",
    "RoomState",
    "agent_source",
    "build_next_scene",
    "get_room",
    "plan_room_state",
]


class RoomState(BaseModel):
    """L'état persistant de la création scène par scène (colonne `memory_json`)."""

    arc: list[ScenePlan] = Field(default_factory=list)      # squelettes ordonnés
    memory: RoomMemory = Field(default_factory=RoomMemory)  # bible + synopsis (avance)
    built: list[str] = Field(default_factory=list)          # ids de scènes déjà créées
    transcripts: dict[str, list[Turn]] = Field(default_factory=dict)  # débat par scène

    def remaining(self) -> list[ScenePlan]:
        return [s for s in self.arc if s.id not in self.built]


def get_room(openai_key: str | None = None) -> tuple[ContractAgent, Drafter]:
    """Le réalisateur (contrat) + les remplisseurs : OpenAI si clé, sinon le Fake."""
    if not openai_key:
        return FakeContractAgent(), FakeDrafter()
    from openai import OpenAI

    from ....features.crew_room.openai_room import OpenAIContractAgent, OpenAIDrafter

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    client = OpenAI(api_key=openai_key)
    return OpenAIContractAgent(client, model), OpenAIDrafter(client, model)


def plan_room_state(arc: list[ScenePlan]) -> RoomState:
    """Ouvre la production : l'arc figé, mémoire vide, rien de construit."""
    return RoomState(arc=arc)


def build_next_scene(
    doc: EditorDocument,
    state: RoomState,
    brief: Brief,
    *,
    director: ContractAgent | None = None,
    drafters: Drafter | None = None,
    openai_key: str | None = None,
) -> tuple[ScenePlan, list[Turn]]:
    """Crée LA prochaine scène non construite via l'atelier (contrat → brouillons →
    mise en commun), l'ajoute au doc, fait avancer la mémoire, met à jour l'état.
    Renvoie (scène, transcript). ``StopIteration`` si tout est déjà construit."""
    skeleton = next(s for s in state.arc if s.id not in state.built)
    if director is None or drafters is None:
        director, drafters = get_room(openai_key)

    scene_brief = SceneBrief(
        id=skeleton.id, title=skeleton.title,
        intention=skeleton.context_text, environment=skeleton.environment_desc,
    )
    result = run_scene_room(
        brief, scene_brief, state.memory, director=director, drafters=drafters
    )
    append_scene(doc, result.scene, result.new_characters)

    # La mémoire AVANCE : bible cumulée + synopsis + transcript conservé.
    state.memory.bible.extend(result.new_characters)
    summary = f"{skeleton.title}: {skeleton.context_text}".strip().rstrip(":")
    state.memory.synopsis_so_far = (
        f"{state.memory.synopsis_so_far} {summary}".strip()
    )
    state.built.append(skeleton.id)
    state.transcripts[skeleton.id] = result.transcript
    return result.scene, result.transcript
