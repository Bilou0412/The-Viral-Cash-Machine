"""Dialoguiste — 2e agent-métier qui réécrit le dossier (même patron que le DA).

Il consomme l'`AgentContext` (la tranche « narration » porteuse des ids d'enfants
audio + les personnages), appelle l'agent dialoguiste, puis **applique** son
résultat au document : réécrit `AudioChild.params["text"]` de chaque réplique,
relocalisée **par id d'enfant**. Le doc est revalidé mais **pas persisté** ici
(la route le fait). Aucun asset n'est régénéré (réécriture seule, coût nul).
"""

from __future__ import annotations

import os

from ....editor.document import ClipBrick, EditorDocument
from ....features.brief.model import Brief
from ....features.crew.fake_dialogue_agent import FakeDialogueAgent
from ....features.crew.model import Dialogue, NarrationRef
from ....features.crew.ports import DialogueAgent
from .context import assemble_context
from .crew import DEFAULT_OPENAI_MODEL, AgentSource, agent_source

__all__ = ["AgentSource", "agent_source", "direct_dialogue", "get_dialogue_agent"]


def get_dialogue_agent(openai_key: str | None = None) -> DialogueAgent:
    """Renvoie le dialoguiste OpenAI si une clé est donnée, sinon le Fake."""
    if not openai_key:
        return FakeDialogueAgent()
    from openai import OpenAI

    from ....features.crew.openai_dialogue_agent import OpenAIDialogueAgent

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIDialogueAgent(OpenAI(api_key=openai_key), model)


def _narration_refs(units: list[dict[str, object]]) -> list[NarrationRef]:
    """La tranche « narration » de l'AgentContext → entrées typées de l'agent."""
    return [
        NarrationRef(id=str(u.get("id", "")), text=str(u.get("text", ""))) for u in units
    ]


def _apply(doc: EditorDocument, dialogue: Dialogue) -> EditorDocument:
    """Applique les répliques réécrites au doc, par id d'enfant audio.

    Ne touche que les enfants renvoyés (map `line_id` → `AudioChild`). Revalide les
    invariants du doc avant de rendre.
    """
    child_by_id = {
        child.id: child
        for brick in doc.bricks
        if isinstance(brick, ClipBrick)
        for child in brick.children
    }
    for line in dialogue.lines:
        text = line.text.strip()
        child = child_by_id.get(line.line_id)
        if child is not None and text:
            child.params["text"] = text
    return EditorDocument.model_validate(doc.model_dump())


def direct_dialogue(
    doc: EditorDocument,
    brief: Brief,
    *,
    agent: DialogueAgent | None = None,
    openai_key: str | None = None,
) -> EditorDocument:
    """Dirige le dialoguiste : réécrit le texte parlé du document.

    Renvoie le doc muté et revalidé (non persisté). Lève `CrewAgentError` si l'agent
    ne produit rien d'exploitable."""
    ctx = assemble_context("dialoguiste", brief=brief, doc=doc)
    lines = _narration_refs(ctx.dossier.get("narration", []))
    characters = {str(k): str(v) for k, v in ctx.dossier.get("characters", {}).items()}
    ag = agent or get_dialogue_agent(openai_key)
    dialogue = ag.write_dialogue(
        tone=brief.ton,
        audience=brief.audience,
        language=brief.langue,
        characters=characters,
        lines=lines,
    )
    return _apply(doc, dialogue)
