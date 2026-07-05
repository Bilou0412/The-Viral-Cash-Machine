"""`VideoPlan` → `EditorDocument` (scènes + briques courtes) — adaptateur PUR.

Miroir neutre de `adventure_to_bricks`, mais piloté par le plan de scènes :
- pour chaque scène, une brique PHOTO d'environnement (contexte figé) ;
- puis un plan court = une brique VIDÉO/PHOTO (+ narration) qui l'animera ;
- l'index `document.Scene` référence ces briques par id (photo d'env + plans).

Durées/modèles paramétrés (défauts = ceux du rail). Aucune I/O, aucun réseau.
"""

from __future__ import annotations

from typing import cast

from ...editor.document import (
    AudioChild,
    Brick,
    ClipBrick,
    EditorDocument,
    GenNode,
    NarrativeContext,
    Scene,
    TimelinePlacement,
)
from .model import VideoPlan

_IMAGE_MODEL = "bytedance/seedream-4.5"
_VIDEO_MODEL = "prunaai/p-video"
_VOICE_MODEL = "minimax/speech-2.8-turbo"
_DEFAULT_NARRATOR_VOICE = "Deep_Voice_Man"
_ENV_PHOTO_DUR = 3.0


def scene_plan_to_document(
    plan: VideoPlan,
    *,
    image_model: str = _IMAGE_MODEL,
    video_model: str = _VIDEO_MODEL,
    voice_model: str = _VOICE_MODEL,
    narrator_voice_id: str = _DEFAULT_NARRATOR_VOICE,
    env_photo_dur: float = _ENV_PHOTO_DUR,
    title: str | None = None,
) -> EditorDocument:
    """Construit le document éditable (briques à plat + index de scènes)."""
    cursor = 0.0

    def place(duration: float) -> TimelinePlacement:
        nonlocal cursor
        pl = TimelinePlacement(track=0, start=cursor, duration=duration)
        cursor += duration
        return pl

    def narr_child(brick_id: str, text: str) -> list[AudioChild]:
        if not text:
            return []
        return [
            AudioChild(
                id=f"{brick_id}__narr",
                role="narration",
                model_ref=voice_model,
                params={"text": text, "voice_id": narrator_voice_id},
            )
        ]

    bricks: list[ClipBrick] = []
    scenes: list[Scene] = []

    for sp in plan.scenes:
        # 1) Photo d'environnement — contexte figé (pas de zoom → IntroSegment sûr).
        env_id = f"{sp.id}_env"
        bricks.append(
            ClipBrick(
                id=env_id,
                kind="photo",
                image=GenNode(model_ref=image_model, params={"prompt": sp.environment_desc}),
                children=[],
                placement=place(env_photo_dur),
            )
        )
        shot_ids = [env_id]
        # Chaque plan vidéo anime la photo d'ENVIRONNEMENT de la scène (contexte
        # figé) : sa 1re frame i2v est cette photo (ref inter-brique, résolue à la
        # génération). C'est ce qui garde le contexte concentré, non dilué.
        env_ref = f"{{brick:{env_id}.image}}"

        # 2) Plans courts qui animent la photo (contexte en mouvement).
        for shot in sp.shots:
            children = narr_child(shot.id, shot.narration_fr)
            if shot.kind == "video":
                brick = ClipBrick(
                    id=shot.id,
                    kind="video",
                    image=GenNode(model_ref=image_model, params={"prompt": shot.visual_desc}),
                    motion=GenNode(
                        model_ref=video_model,
                        params={
                            "prompt": shot.motion_desc,
                            "duration": shot.duration_s,
                            "image": env_ref,
                        },
                    ),
                    children=children,
                    placement=place(shot.duration_s),
                )
            else:
                brick = ClipBrick(
                    id=shot.id,
                    kind="photo",
                    image=GenNode(model_ref=image_model, params={"prompt": shot.visual_desc}),
                    children=children,
                    placement=place(shot.duration_s),
                )
            bricks.append(brick)
            shot_ids.append(shot.id)

        scenes.append(
            Scene(
                id=sp.id,
                title=sp.title,
                context=NarrativeContext(text=sp.context_text, art_direction=sp.art_direction),
                environment_photo_ref=env_id,
                shot_ids=shot_ids,
            )
        )

    context = NarrativeContext(
        text=plan.global_context,
        characters=plan.characters,
        art_direction=plan.art_direction,
    )
    return EditorDocument(
        title=title or plan.title,
        global_context=context,
        bricks=cast("list[Brick]", bricks),
        scenes=scenes,
    )
