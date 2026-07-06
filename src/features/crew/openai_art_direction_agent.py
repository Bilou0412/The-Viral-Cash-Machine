"""Directeur artistique OpenAI — réécrit l'identité visuelle d'une vidéo.

Brief métier : un DA de cinéma pose un style commun et réécrit le prompt image
(la photo d'environnement) de chaque scène pour qu'elles partagent la même
identité, en restant **concrètes et en ANGLAIS** (les modèles image l'exigent),
quel que soit la langue de narration. Sortie JSON stricte parsée via Pydantic
(mirror `openai_distribution_agent`, import paresseux du SDK).
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import ValidationError

from .model import ArtDirection, SceneRef
from .ports import CrewAgentError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_SYSTEM = (
    "You are a film ART DIRECTOR for short-form vertical (9:16) videos. Give the "
    "whole video ONE coherent visual identity, then REWRITE each scene's "
    "environment image prompt so they all share it (same palette, lighting, "
    "texture, era). Keep each scene's actual location/subject — only elevate the "
    "style.\n"
    'Return JSON {"art_direction", "scenes":[{"scene_id","environment_prompt"}]}:\n'
    '- "art_direction": ENGLISH, one line describing the common look (palette, '
    "lighting, grain, lens/era);\n"
    '- one entry per input scene, SAME scene_id;\n'
    '- "environment_prompt": ENGLISH (image models expect English) regardless of '
    "narration language. A vivid STILL image prompt of that scene's setting: "
    "location, time of day, lighting, mood, textures — consistent with the shared "
    "art direction. NO camera movement (it is a photo), NO on-screen text, NO "
    "watermark.\n"
    "Output JSON only."
)


class OpenAIArtDirectionAgent:
    """Implémente `ArtDirectionAgent` via GPT (structured output JSON)."""

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
            raise CrewAgentError(f"Art direction request failed: {e}") from e
        content: str = resp.choices[0].message.content or ""
        return content

    def direct(
        self,
        *,
        tone: str,
        platform: str,
        language: str,
        art_direction: str,
        scenes: list[SceneRef],
    ) -> ArtDirection:
        scene_payload = json.dumps(
            [{"scene_id": s.id, "title": s.title, "environment": s.environment} for s in scenes],
            ensure_ascii=False,
        )
        user = (
            f"Platform: {platform}\nNarration language: {language}\n"
            f"Tone: {tone or '(unspecified)'}\n"
            f"Current art direction: {art_direction or '(none)'}\n"
            f"Scenes: {scene_payload}\nRewrite the visual identity now."
        )
        try:
            out = ArtDirection.model_validate_json(self._chat_json(_SYSTEM, user))
        except ValidationError as e:
            raise CrewAgentError(
                "Le directeur artistique n'a pas pu réécrire l'identité visuelle. Réessaie."
            ) from e
        if not out.scenes:
            raise CrewAgentError(
                "Le directeur artistique a renvoyé une direction vide. Réessaie."
            )
        return out
