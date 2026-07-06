"""Attaché de presse / Growth OpenAI — écrit la fiche de sortie d'une vidéo.

Brief métier : maximiser la rétention et la portée sur TikTok/Shorts/Reels, en
français. Sortie JSON stricte parsée via Pydantic (mirror `openai_scene_decomposer`,
import paresseux du SDK).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from .model import DistributionKit
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI


class OpenAIDistributionAgent:
    """Implémente `DistributionAgent` via GPT (structured output JSON)."""

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
            raise CrewAgentError(f"Distribution request failed: {e}") from e
        content: str = resp.choices[0].message.content or ""
        return content

    def write_kit(
        self, *, title: str, synopsis: str, narration: str = ""
    ) -> DistributionKit:
        system = (
            "You are a French-speaking short-form growth strategist (TikTok / Reels / "
            "Shorts). Write the release kit for a vertical 9:16 video that MAXIMIZES "
            "retention and reach.\n"
            'Return JSON {"title", "description", "hashtags", "hook"}:\n'
            '- "title": FRENCH, punchy, scroll-stopping, <= 80 chars, no clickbait lies;\n'
            '- "description": FRENCH, 1-3 sentences, ends with a light call to action;\n'
            '- "hashtags": 4 to 8 relevant FRENCH/EN hashtags, each starting with "#";\n'
            '- "hook": FRENCH, the first spoken line (<= 12 words) that grabs in 1 second.\n'
            "Output JSON only."
        )
        user = (
            f"Video title: {title}\nSynopsis: {synopsis}\n"
            f"Opening narration: {narration or '(none)'}\nWrite the release kit now."
        )
        try:
            kit = DistributionKit.model_validate_json(self._chat_json(system, user))
        except ValidationError as e:
            raise CrewAgentError(
                "L'attaché de presse n'a pas pu écrire la fiche de sortie. Réessaie."
            ) from e
        if not kit.title.strip():
            raise CrewAgentError(
                "L'attaché de presse a renvoyé une fiche vide. Réessaie."
            )
        return kit
