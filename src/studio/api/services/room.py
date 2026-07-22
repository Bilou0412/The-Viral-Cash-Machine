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
from ....features.assets.models import VIDEO_MODEL, max_coherent_duration_s
from ....features.brief.model import Brief
from ....features.crew_room import (
    ContractAgent,
    Drafter,
    FakeContractAgent,
    FakeDrafter,
    FakeReviewer,
    Reviewer,
    RoomMemory,
    SceneBrief,
    Turn,
    run_scene_room,
)
from ....features.scenes import ScenePlan, append_scene
from ....features.scenes.model import VideoPlan
from ....features.scenes.split import split_overlong_shots
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


def get_room(
    openai_key: str | None = None,
) -> tuple[ContractAgent, Drafter, Reviewer]:
    """Le réalisateur (contrat) + les remplisseurs + le SUPERVISEUR : OpenAI si clé,
    sinon le Fake. Le superviseur pilote la boucle de révision (la boîte de prod)."""
    if not openai_key:
        return FakeContractAgent(), FakeDrafter(), FakeReviewer()
    from openai import OpenAI

    from ....features.crew_room.openai_room import (
        OpenAIContractAgent,
        OpenAIDrafter,
        OpenAIReviewer,
    )

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    client = OpenAI(api_key=openai_key)
    return (
        OpenAIContractAgent(client, model),
        OpenAIDrafter(client, model),
        OpenAIReviewer(client, model),
    )


def plan_room_state(arc: list[ScenePlan]) -> RoomState:
    """Ouvre la production : l'arc figé, mémoire vide, rien de construit."""
    return RoomState(arc=arc)


def _split_to_horizon(scene: ScenePlan) -> ScenePlan:
    """Borne les plans de la scène à l'horizon i2v (5 s) : un plan trop long est SCINDÉ
    en sous-plans de durée égale ≤ horizon (on ne rabote pas). Réutilise le filet du
    chemin scènes ; garantit la hiérarchie « bouts de 5 s » aussi pour la table ronde."""
    plan = VideoPlan(scenes=[scene])
    split = split_overlong_shots(plan, max_coherent_s=max_coherent_duration_s(VIDEO_MODEL))
    return split.scenes[0] if split.scenes else scene


def build_next_scene(
    doc: EditorDocument,
    state: RoomState,
    brief: Brief,
    *,
    director: ContractAgent | None = None,
    drafters: Drafter | None = None,
    reviewer: Reviewer | None = None,
    openai_key: str | None = None,
) -> tuple[ScenePlan, list[Turn]]:
    """Crée LA prochaine scène non construite via l'atelier (contrat → brouillons parallèles
    → mise en commun → révision pilotée par le superviseur), la borne à 5 s, l'ajoute au doc,
    fait avancer la mémoire. Renvoie (scène, transcript). ``StopIteration`` si tout est fait."""
    skeleton = next(s for s in state.arc if s.id not in state.built)
    if director is None or drafters is None or reviewer is None:
        director, drafters, reviewer = get_room(openai_key)

    scene_brief = SceneBrief(
        id=skeleton.id, title=skeleton.title,
        intention=skeleton.intention_scene, environment=skeleton.environment_desc,
    )
    result = run_scene_room(
        brief, scene_brief, state.memory,
        director=director, drafters=drafters, reviewer=reviewer,
    )
    scene = _split_to_horizon(result.scene)
    append_scene(doc, scene, result.new_characters)

    # La mémoire AVANCE : bible cumulée + synopsis + transcript conservé.
    state.memory.bible.extend(result.new_characters)
    summary = f"{skeleton.title}: {skeleton.intention_scene}".strip().rstrip(":")
    state.memory.synopsis_so_far = (
        f"{state.memory.synopsis_so_far} {summary}".strip()
    )
    state.built.append(skeleton.id)
    state.transcripts[skeleton.id] = result.transcript
    return scene, result.transcript
