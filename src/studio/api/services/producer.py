"""Producer service — sélectionne l'agent producteur et lance la proposition.

Mirror de `scenes.get_scene_decomposer` / `crew.get_distribution_agent` : clé
OpenAI → impl réelle (import paresseux) ; sinon le Fake déterministe (offline/
tests). L'agent producteur propose le Brief que le producteur humain édite.
"""

from __future__ import annotations

import os
from typing import Literal

from ....features.brief.fake_producer_agent import FakeProducerAgent
from ....features.brief.model import Brief
from ....features.brief.ports import ProducerAgent

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"

AgentSource = Literal["openai", "fake"]


def producer_source(openai_key: str | None) -> AgentSource:
    """Quel moteur : réel si clé OpenAI présente, sinon le Fake déterministe."""
    return "openai" if openai_key else "fake"


def get_producer_agent(openai_key: str | None = None) -> ProducerAgent:
    """Renvoie le producteur OpenAI si une clé est donnée, sinon le Fake."""
    if not openai_key:
        return FakeProducerAgent()
    from openai import OpenAI

    from ....features.brief.openai_producer_agent import OpenAIProducerAgent

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIProducerAgent(OpenAI(api_key=openai_key), model)


def propose_brief(
    idea: str,
    *,
    partial: Brief | None = None,
    agent: ProducerAgent | None = None,
    openai_key: str | None = None,
) -> Brief:
    """Idée (+ champs déjà décidés) → Brief complété via le producteur choisi."""
    ag = agent or get_producer_agent(openai_key)
    return ag.draft_brief(idea=idea, partial=partial)
