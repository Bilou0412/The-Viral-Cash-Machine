"""Crew service — sélectionne les agents-métiers et les lance.

Premier agent dédié : l'attaché de presse / Growth (fiche de sortie). Mirror de
`scenes.get_scene_decomposer` : clé OpenAI → impl réelle (import paresseux) ;
sinon le Fake déterministe (offline/tests).
"""

from __future__ import annotations

import os
from typing import Literal

from ....editor.document import ClipBrick, EditorDocument
from ....features.crew.fake_distribution_agent import FakeDistributionAgent
from ....features.crew.model import DistributionKit
from ....features.crew.ports import DistributionAgent

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

AgentSource = Literal["openai", "fake"]


def agent_source(openai_key: str | None) -> AgentSource:
    """Quel moteur : réel si clé OpenAI présente, sinon le Fake déterministe."""
    return "openai" if openai_key else "fake"


def get_distribution_agent(openai_key: str | None = None) -> DistributionAgent:
    """Renvoie l'attaché de presse OpenAI si une clé est donnée, sinon le Fake."""
    if not openai_key:
        return FakeDistributionAgent()
    from openai import OpenAI

    from ....features.crew.openai_distribution_agent import OpenAIDistributionAgent

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIDistributionAgent(OpenAI(api_key=openai_key), model)


def _context_of(doc: EditorDocument) -> tuple[str, str, str]:
    """(titre, synopsis, 1re narration) extraits du document pour briefer l'agent."""
    synopsis = doc.global_context.text.strip()
    if not synopsis:
        # À défaut : concatène les prompts visuels des scènes (le storyboard).
        parts = [s.context.text for s in doc.scenes if s.context.text.strip()]
        synopsis = " ".join(parts)[:400]
    narration = ""
    for brick in doc.bricks:
        if isinstance(brick, ClipBrick):
            for child in brick.children:
                text = child.params.get("text")
                if isinstance(text, str) and text.strip():
                    narration = text.strip()
                    break
        if narration:
            break
    return doc.title, synopsis, narration


def generate_distribution_kit(
    doc: EditorDocument,
    *,
    agent: DistributionAgent | None = None,
    openai_key: str | None = None,
) -> DistributionKit:
    """Document → fiche de sortie via l'attaché de presse choisi."""
    title, synopsis, narration = _context_of(doc)
    ag = agent or get_distribution_agent(openai_key)
    return ag.write_kit(title=title, synopsis=synopsis, narration=narration)
