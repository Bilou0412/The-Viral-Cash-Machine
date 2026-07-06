"""Producteur OpenAI — propose un Brief complet à partir d'une idée.

Brief métier : jouer le producteur qui **oriente** — remplir objectif/audience/
plateforme/durée/coût/ton avec des défauts court-format sensés, pour que le
producteur humain édite plutôt qu'il ne parte d'une page blanche. Sortie JSON
stricte parsée via Pydantic (mirror `openai_distribution_agent`, import paresseux).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .model import Brief
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_SYSTEM = (
    "You are a French-speaking short-form video PRODUCER. From a raw idea, PROPOSE "
    "a complete brief so the human producer edits it rather than filling a blank "
    "form. Fill sensible defaults for vertical 9:16 TikTok/Reels/Shorts.\n"
    'Return JSON {"objectif","audience","plateforme","duree_s","budget_usd","ton","langue","notes"}:\n'
    '- "objectif": FRENCH, why this video exists (the goal), 1 sentence;\n'
    '- "audience": FRENCH, who it targets (age, interest);\n'
    '- "plateforme": one of "tiktok" | "reels" | "shorts" | "youtube_short";\n'
    '- "duree_s": target TOTAL duration in seconds (number, 15-60 for short-form);\n'
    '- "budget_usd": cost ceiling in USD (number, 0 if unknown);\n'
    '- "ton": FRENCH, the mood/tone in a few words;\n'
    '- "langue": narration language code ("fr" by default);\n'
    '- "notes": FRENCH, any short orientation note (may be empty).\n'
    "Respect any fields already decided (given below) — do not override them.\n"
    "Output JSON only."
)


class OpenAIProducerAgent:
    """Implémente `ProducerAgent` via GPT (structured output JSON)."""

    def __init__(self, client: OpenAI, model: str) -> None:
        self.client = client
        self.model = model

    def _chat_json(self, system: str, user: str) -> str:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except Exception as e:  # erreur réseau / API
            raise CrewAgentError(f"Producer request failed: {e}") from e
        content: str = resp.choices[0].message.content or ""
        return content

    def draft_brief(self, *, idea: str, partial: Brief | None = None) -> Brief:
        decided = json.dumps((partial or Brief()).model_dump(), ensure_ascii=False)
        user = (
            f"Idea: {idea.strip() or '(none)'}\n"
            f"Already-decided fields (respect non-empty ones): {decided}\n"
            "Propose the complete brief now."
        )
        try:
            brief = Brief.model_validate_json(self._chat_json(_SYSTEM, user))
        except ValidationError as e:
            raise CrewAgentError(
                "Le producteur n'a pas pu proposer de brief exploitable. Réessaie."
            ) from e
        if not brief.objectif.strip():
            raise CrewAgentError(
                "Le producteur a renvoyé un brief vide. Réessaie."
            )
        return brief
