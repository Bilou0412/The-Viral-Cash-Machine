"""Décrypteur de scènes OpenAI — deux phases, neutre (aucun CYOA).

Phase MACRO : idée → liste de scènes (titre + photo d'environnement + intention).
Phase MICRO : chaque scène → plans courts (visuel EN, mouvement EN, narration FR),
en portant un résumé courant pour la continuité de l'arc. Miroir structurel de
`openai_adventure_decomposer._decompose_chronology`, prompts génériques.

Convention langue : ``*_desc`` = anglais (prompt visuel) ; narration = français.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from .model import ScenePlan, ShotPlan, VideoPlan
from .ports import DEFAULT_SCENES, SceneDecompositionError

if TYPE_CHECKING:  # `openai` absent hors conteneur — import paresseux.
    from openai import OpenAI

_MAX_SHOTS = 4


class _SceneSk(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = ""
    title: str = ""
    environment_desc: str = ""
    intention: str = ""


class _ScenesOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    scenes: list[_SceneSk] = []


class _ShotOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = ""
    kind: str = "video"
    visual_desc: str = ""
    motion_desc: str = ""
    narration_fr: str = ""
    duration_s: float = 4.0


class _ShotsOut(BaseModel):
    model_config = ConfigDict(extra="ignore")
    shots: list[_ShotOut] = []


def _kind_of(raw: str) -> Literal["video", "photo"]:
    return "photo" if raw.strip().lower() == "photo" else "video"


class OpenAISceneDecomposer:
    """Implémente `SceneVideoDecomposer` via GPT (structured output JSON)."""

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
            raise ValueError(f"Scene decomposition request failed: {e}") from e
        content: str = resp.choices[0].message.content or ""
        return content

    def _plan_scenes(
        self, prompt: str, style_identity: str, n_scenes: int
    ) -> list[_SceneSk]:
        """MACRO : l'arc en `n_scenes` scènes (une par contexte concentré)."""
        system = (
            "You are a short-form vertical (9:16) video director for TikTok/Reels/Shorts. "
            "Plan a video as an ORDERED list of SCENES forming a tight arc: HOOK (grab in "
            "the first seconds), BUILD (raise tension/curiosity), PAYOFF (a beat that lands). "
            "A SCENE is ONE concentrated context — a single location and moment that must "
            "NOT dilute: everything in it shares the same place and mood.\n"
            f'Return JSON {{"scenes": [...]}} with EXACTLY {n_scenes} scenes, each with:\n'
            '- "id": short slug;\n'
            '- "title": short FRENCH label;\n'
            '- "environment_desc": ENGLISH. The establishing PHOTO of the setting — a still '
            "image prompt. Concrete and vivid: location, time of day, lighting, mood, "
            "textures. NO camera movement (it is a photo), NO on-screen text, NO watermark;\n"
            '- "intention": what happens in this scene and why it matters to the arc '
            "(distinct per scene).\n"
            "Name any character with a FRENCH first name (never 'Character A'). "
            "Output JSON only."
        )
        if style_identity.strip():
            system += f"\nSTYLE / IDENTITY (apply to every scene): {style_identity.strip()}"
        user = f"Idea / pitch: {prompt}\nPlan EXACTLY {n_scenes} scenes now."
        try:
            out = _ScenesOut.model_validate_json(self._chat_json(system, user))
        except ValidationError:
            return []
        return out.scenes

    def _expand_scene(
        self, sk: _SceneSk, style_identity: str, running_summary: str
    ) -> list[ShotPlan]:
        """MICRO : la scène → plans COURTS qui animent sa photo d'environnement."""
        system = (
            "You are a director breaking ONE scene into SHORT shots (3 to 5 seconds each) "
            "that ANIMATE the scene's environment photo. Every shot STAYS INSIDE that same "
            "environment (same location, same mood) — never cut to a new place. Keep the "
            "context concentrated.\n"
            f'Return JSON {{"shots": [...]}} with 2 to {_MAX_SHOTS} shots, each with:\n'
            '- "id": short slug;\n'
            '- "kind": "video" (default) or "photo";\n'
            '- "visual_desc": ENGLISH. What we see in THIS shot within the environment — '
            "concrete subject, framing, detail; consistent with the environment; "
            "NO on-screen text;\n"
            '- "motion_desc": ENGLISH. STRICTLY STATIC CAMERA (locked-off tripod). Describe '
            "the SUBJECT'S action, never a camera move (no pan/zoom/dolly/handheld) — the "
            "model drifts otherwise;\n"
            '- "narration_fr": FRENCH. One short, natural, spoken sentence (French first '
            "names for people);\n"
            '- "duration_s": 3 to 5.\n'
            "The FIRST shot should hook. No on-screen text. Output JSON only."
        )
        if style_identity.strip():
            system += f"\nSTYLE / IDENTITY: {style_identity.strip()}"
        user = (
            f"Scene: {sk.title}\nEnvironment: {sk.environment_desc}\n"
            f"Intention: {sk.intention}\nStory so far: {running_summary or '(start)'}\n"
            "Break this scene into short shots now."
        )
        try:
            out = _ShotsOut.model_validate_json(self._chat_json(system, user))
        except ValidationError:
            return []
        shots: list[ShotPlan] = []
        for i, s in enumerate(out.shots[:_MAX_SHOTS]):
            shots.append(
                ShotPlan(
                    id=s.id or f"{sk.id or 'sc'}_sh{i + 1}",
                    kind=_kind_of(s.kind),
                    visual_desc=s.visual_desc,
                    motion_desc=s.motion_desc,
                    narration_fr=s.narration_fr,
                    duration_s=max(2.0, min(6.0, s.duration_s or 4.0)),
                )
            )
        return shots

    def decompose_video(
        self, prompt: str, *, style_identity: str = "", n_scenes: int = DEFAULT_SCENES
    ) -> VideoPlan:
        n = max(1, n_scenes)
        skeletons = self._plan_scenes(prompt, style_identity, n)
        if not skeletons:
            raise SceneDecompositionError(
                "L'IA n'a pas pu découper cette idée en scènes. Reformule ton idée "
                "ou réessaie."
            )
        scenes: list[ScenePlan] = []
        summary_parts: list[str] = []
        for i, sk in enumerate(skeletons[:n]):
            sid = sk.id or f"s{i + 1}"
            shots = self._expand_scene(sk, style_identity, " ".join(summary_parts))
            if not shots:
                # Micro illisible : garder la scène générable avec un plan minimal
                # qui anime sa photo d'environnement (plutôt qu'une scène morte).
                shots = [
                    ShotPlan(
                        id=f"{sid}_sh1",
                        kind="video",
                        visual_desc=sk.environment_desc,
                        motion_desc="slow push in, static camera",
                        narration_fr="",
                        duration_s=4.0,
                    )
                ]
            scenes.append(
                ScenePlan(
                    id=sid,
                    title=sk.title or f"Scène {i + 1}",
                    environment_desc=sk.environment_desc,
                    context_text=sk.intention,
                    art_direction=style_identity,
                    shots=shots,
                )
            )
            if sk.intention:
                summary_parts.append(sk.intention)
        return VideoPlan(
            title=prompt[:60] or "Nouvelle vidéo",
            global_context=prompt,
            art_direction=style_identity,
            scenes=scenes,
        )
