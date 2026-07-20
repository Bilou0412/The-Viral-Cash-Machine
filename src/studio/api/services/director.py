"""Réalisateur — assemble une PARTIE (fragment v5) depuis une description NL, puis
l'appende à un `EditorDocument` (TPLM-D, le cœur de la co-construction).

Le réalisateur VOIT le catalogue d'effets de montage via `AgentContext.effects`
(`context.py`) et n'en pose QUE ceux-là ; son `FragmentPlan` (beats à effets) devient
des `ClipBrick` v5 (`fragment_to_bricks`, effets en IR), posés À LA SUITE de la timeline
existante. Aucune génération — forme seulement (idempotence de forme). Mirror `crew.py`
pour la sélection Fake/OpenAI ; écrit dans le document comme `art_direction.py`.
"""

from __future__ import annotations

import os

from ....editor.document import Brick, ClipBrick, EditorDocument
from ....features.brief.model import Brief
from ....features.crew import fragment_to_bricks
from ....features.crew.fake_director_agent import FakeDirectorAgent
from ....features.crew.ports import DirectorAgent
from .context import assemble_context
from .crew import DEFAULT_OPENAI_MODEL, AgentSource, agent_source

__all__ = ["AgentSource", "agent_source", "assemble_part", "get_director_agent"]


def get_director_agent(openai_key: str | None = None) -> DirectorAgent:
    """Renvoie le réalisateur OpenAI si une clé est donnée, sinon le Fake déterministe."""
    if not openai_key:
        return FakeDirectorAgent()
    from openai import OpenAI

    from ....features.crew.openai_director_agent import OpenAIDirectorAgent

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIDirectorAgent(OpenAI(api_key=openai_key), model)


def _timeline_end(doc: EditorDocument) -> float:
    """Fin de la timeline posée (on appende le nouveau fragment juste après)."""
    ends = [
        b.placement.start + b.placement.duration
        for b in doc.bricks
        if isinstance(b, ClipBrick) and b.placement.duration > 0
    ]
    return round(max(ends), 2) if ends else 0.0


def _uniquify(bricks: list[ClipBrick], existing: set[str]) -> list[ClipBrick]:
    """Garantit des ids uniques (invariant `EditorDocument`) — vs l'existant ET entre eux.

    Si un id collisionne, on le suffixe (`intro_env` → `intro_env_2`) et on répercute
    sur les ids d'enfants qui en dérivent (`{bid}__narr`), pour ne rien orpheliner.
    """
    seen = set(existing)
    for b in bricks:
        if b.id not in seen:
            seen.add(b.id)
            continue
        base, n = b.id, 2
        while f"{base}_{n}" in seen:
            n += 1
        new_id = f"{base}_{n}"
        for child in b.children:
            if child.id.startswith(base):
                child.id = new_id + child.id[len(base):]
        b.id = new_id
        seen.add(new_id)
    return bricks


def assemble_part(
    doc: EditorDocument,
    description: str,
    *,
    part: str = "intro",
    brief: Brief | None = None,
    agent: DirectorAgent | None = None,
    openai_key: str | None = None,
) -> EditorDocument:
    """Assemble une partie depuis `description` (langage naturel) et l'appende au document.

    Renvoie le doc muté + revalidé (non persisté ; la route le sauve). Lève
    `CrewAgentError` si l'agent ne produit rien d'exploitable."""
    the_brief = brief or Brief()
    ctx = assemble_context("realisateur", brief=the_brief, doc=doc)
    effects = [e.name for e in ctx.effects]
    ag = agent or get_director_agent(openai_key)
    plan = ag.assemble(
        description=description,
        part=part.strip() or "part",
        effects=effects,
        language=the_brief.langue or "fr",
    )
    new_bricks = _uniquify(
        fragment_to_bricks(plan, start=_timeline_end(doc)),
        {b.id for b in doc.bricks},
    )
    updated: list[Brick] = [*doc.bricks, *new_bricks]
    return EditorDocument.model_validate(doc.model_copy(update={"bricks": updated}).model_dump())
