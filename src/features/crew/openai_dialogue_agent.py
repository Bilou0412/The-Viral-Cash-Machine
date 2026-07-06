"""Dialoguiste OpenAI — réécrit le texte parlé d'une vidéo.

Brief métier : un dialoguiste réécrit chaque réplique pour qu'elle soit courte,
naturelle et parlée, dans la **langue de narration** demandée, cohérente avec le
ton/l'audience et les personnages. Rattache chaque réécriture à son `line_id`.
Sortie JSON stricte parsée via Pydantic (mirror `openai_art_direction_agent`).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .model import Dialogue, NarrationRef
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_SYSTEM = (
    "You are a DIALOGUE writer for short-form vertical videos. Rewrite each spoken "
    "line to be SHORT, natural and punchy — the kind of line a person actually says "
    "out loud. Keep the meaning and the running story; match the tone and audience.\n"
    "Write in the requested narration language (default French). Use French first "
    "names for people (never 'Character A'). Keep each line to ONE sentence.\n"
    'Return JSON {"lines":[{"line_id","text"}]}: one entry per input line, SAME '
    'line_id, "text" = the rewritten spoken line. Do NOT drop or add lines. Output '
    "JSON only."
)


class OpenAIDialogueAgent:
    """Implémente `DialogueAgent` via GPT (structured output JSON)."""

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
            raise CrewAgentError(f"Dialogue request failed: {e}") from e
        content: str = resp.choices[0].message.content or ""
        return content

    def write_dialogue(
        self,
        *,
        tone: str,
        audience: str,
        language: str,
        characters: dict[str, str],
        lines: list[NarrationRef],
    ) -> Dialogue:
        payload = json.dumps(
            [{"line_id": line.id, "text": line.text} for line in lines],
            ensure_ascii=False,
        )
        user = (
            f"Narration language: {language}\nTone: {tone or '(unspecified)'}\n"
            f"Audience: {audience or '(unspecified)'}\n"
            f"Characters: {json.dumps(characters, ensure_ascii=False) or '{}'}\n"
            f"Lines: {payload}\nRewrite every line now."
        )
        try:
            out = Dialogue.model_validate_json(self._chat_json(_SYSTEM, user))
        except ValidationError as e:
            raise CrewAgentError(
                "Le dialoguiste n'a pas pu réécrire les répliques. Réessaie."
            ) from e
        if not out.lines:
            raise CrewAgentError(
                "Le dialoguiste a renvoyé un texte vide. Réessaie."
            )
        return out
