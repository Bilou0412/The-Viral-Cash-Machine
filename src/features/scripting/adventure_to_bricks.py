"""AdventureScript → arbre de `ClipBrick` — adaptateur PUR (R1 du ROADMAP).

Miroir de `adventure_to_spec`, mais vers le format d'AUTORING éditable (briques
composites) plutôt que vers le `VideoSpec` de rendu. C'est le chaînon
« l'IA écrit → je révise en briques » : chaque asset que l'épisode va générer
apparaît comme un **nœud de brique**, pour être revu / édité / régénéré ciblé.

Ancré sur `plan_episode_assets` (la source unique « quels assets un épisode
produit ») : on GROUPE ses `PlannedAsset` en briques —

- un beat vidéo (`X.frame` image + `X.motion` vidéo) → brique **VIDÉO** (image =
  first-frame, motion = animation) ;
- une image seule (`char_reference`, `choice.i`) → brique **PHOTO** ;
- une narration (`X.narration`) → enfant `narration` de la brique de ce beat (la
  narration de transition se greffe sur l'intro ; celle du choix sur `choice.0`).

**Couverture 1:1** : le multiset des prompts image / prompts motion / textes de
narration des briques est IDENTIQUE à celui de `plan_episode_assets` — donc à
celui de `adventure_to_spec`. Les overlays de montage (countdown, plaques de nom,
transition eye-open) ne sont PAS des assets génératifs → hors briques (montage).

Module PUR : aucune I/O, aucun réseau.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, cast

from ...editor.document import (
    AudioChild,
    Brick,
    ClipBrick,
    EditorDocument,
    GenNode,
    NarrativeContext,
    TimelinePlacement,
)
from ...studio.api.services.generation_plan import PlannedAsset, plan_episode_assets
from .adventure import AdventureScript
from .adventure_to_prompts import Side
from .themes import Theme

# Modèles par défaut (slot quality-price du registry / défauts projet).
_IMAGE_MODEL = "bytedance/seedream-4.5"
_VIDEO_MODEL = "prunaai/p-video"
_VOICE_MODEL = "minimax/speech-2.8-turbo"

# Voix narrateur par défaut — aligne le VoiceAsset produit sur celui d'
# `adventure_to_spec` (défaut "Deep_Voice_Man"). Surcharge possible (conteur cloné).
_DEFAULT_NARRATOR_VOICE = "Deep_Voice_Man"

# Durées nominales de placement (l'agencement ; le rendu dérive la vraie durée).
_VIDEO_DUR = 5.0
_PHOTO_DUR = 4.0


def _brick_id(round_index: Optional[int], beat: str) -> str:
    prefix = "ep" if round_index is None else f"r{round_index}"
    return f"{prefix}_{beat}"


def adventure_to_bricks(
    script: AdventureScript,
    side: Side = "left",
    theme: Optional[Theme] = None,
    narrator_voice_id: str = _DEFAULT_NARRATOR_VOICE,
) -> List[ClipBrick]:
    """Dérive la liste ordonnée de `ClipBrick` éditables d'un épisode.

    Ordre timeline : intro (référence perso) → par round (action, environment,
    face-cam, 2 choix, fatal, survival) → épilogue. Prompts/textes proviennent de
    `plan_episode_assets` (mêmes valeurs que `adventure_to_spec`).
    """
    planned = plan_episode_assets(script, side, theme)
    idx: Dict[Tuple[Optional[int], str], PlannedAsset] = {
        (p.round_index, p.beat): p for p in planned
    }

    def img(ri: Optional[int], beat: str) -> str:
        p = idx.get((ri, beat))
        return (p.image_prompt or "") if p else ""

    def mot(ri: Optional[int], beat: str) -> str:
        p = idx.get((ri, beat))
        return (p.motion_prompt or "") if p else ""

    def txt(ri: Optional[int], beat: str) -> str:
        p = idx.get((ri, beat))
        return (p.text or "") if p else ""

    cursor = 0.0

    def place(duration: float) -> TimelinePlacement:
        nonlocal cursor
        pl = TimelinePlacement(track=0, start=cursor, duration=duration)
        cursor += duration
        return pl

    def narr_child(brick_id: str, ri: Optional[int], beat: str) -> AudioChild:
        return AudioChild(
            id=f"{brick_id}__narr",
            role="narration",
            model_ref=_VOICE_MODEL,
            params={"text": txt(ri, beat), "voice_id": narrator_voice_id},
        )

    def video_brick(ri: Optional[int], beat: str, narr_beat: Optional[str]) -> ClipBrick:
        bid = _brick_id(ri, beat)
        children = [narr_child(bid, ri, narr_beat)] if narr_beat else []
        return ClipBrick(
            id=bid,
            kind="video",
            image=GenNode(model_ref=_IMAGE_MODEL, params={"prompt": img(ri, f"{beat}.frame")}),
            motion=GenNode(model_ref=_VIDEO_MODEL, params={"prompt": mot(ri, f"{beat}.motion")}),
            children=children,
            placement=place(_VIDEO_DUR),
        )

    def photo_brick(
        ri: Optional[int], beat_id: str, image_prompt: str, narr_beat: Optional[str]
    ) -> ClipBrick:
        bid = _brick_id(ri, beat_id)
        children = [narr_child(bid, ri, narr_beat)] if narr_beat else []
        return ClipBrick(
            id=bid,
            kind="photo",
            image=GenNode(model_ref=_IMAGE_MODEL, params={"prompt": image_prompt}),
            children=children,
            placement=place(_PHOTO_DUR),
        )

    bricks: List[ClipBrick] = []

    # 1) INTRO : image de référence perso + narration de transition (narrateur).
    bricks.append(
        photo_brick(None, "intro", img(None, "char_reference"), "transition.narration")
    )

    # 2) N rounds (N-safe : itère les rounds du script).
    for i in range(len(script.rounds)):
        bricks.append(video_brick(i, "action", "action.narration"))
        bricks.append(video_brick(i, "environment", "environment.narration"))
        bricks.append(video_brick(i, "character", None))  # face-cam : voix native
        bricks.append(photo_brick(i, "choice0", img(i, "choice.0"), "choice.narration"))
        bricks.append(photo_brick(i, "choice1", img(i, "choice.1"), None))
        bricks.append(video_brick(i, "fatal", "fatal.narration"))
        bricks.append(video_brick(i, "survival", "survival.narration"))

    # 3) ÉPILOGUE (l'autre perso).
    bricks.append(video_brick(None, "epilogue", "epilogue.narration"))
    return bricks


def adventure_to_document(
    script: AdventureScript,
    side: Side = "left",
    theme: Optional[Theme] = None,
    narrator_voice_id: str = _DEFAULT_NARRATOR_VOICE,
    title: str = "Aventure",
) -> EditorDocument:
    """Emballe les briques dans un `EditorDocument` prêt pour la revue (R2) et le
    compilateur `document_to_spec`. Le contexte récit porte les deux persos."""
    context = NarrativeContext(
        characters={
            script.char_left_name: script.char_left_desc,
            script.char_right_name: script.char_right_desc,
        },
        art_direction=theme.da if theme is not None else "",
    )
    bricks = adventure_to_bricks(script, side, theme, narrator_voice_id)
    return EditorDocument(
        title=title,
        global_context=context,
        bricks=cast("List[Brick]", bricks),
    )
