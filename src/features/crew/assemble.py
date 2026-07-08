"""`FragmentPlan` → briques v5 (`ClipBrick`) — le fragment co-construit devient de l'IR.

Le réalisateur produit un `FragmentPlan` (beats à effets) ; ce builder DÉTERMINISTE le
matérialise en `ClipBrick` sur le rail v5, en posant les effets comme DONNÉES IR
(`countdown`, `intro_eye_open`, `nameplates`, cf. TPLM-B). Aucune génération, aucun
prompt écrit à la main hors rail : chaque beat porte un `ShotBrief` (structuré, donc
descriptible/recompilable) et son sujet sert de prompt image initial.

C'est la brique « forme » de la co-construction : idempotence de forme (même plan →
même fragment). Un service l'appendra à un `EditorDocument` (sauvé comme template).
"""

from __future__ import annotations

from ...editor.document import (
    AudioChild,
    ClipBrick,
    CountdownSpec,
    GenNode,
    NameplateBrief,
    ShotBrief,
    TimelinePlacement,
)
from .model import BeatPlan, FragmentPlan


def _nameplates(beat: BeatPlan) -> list[NameplateBrief]:
    return [NameplateBrief(text=n.text, side=n.side) for n in beat.nameplates if n.text]


def _narration(beat_id: str, text: str) -> list[AudioChild]:
    t = text.strip()
    if not t:
        return []
    return [AudioChild(id=f"{beat_id}__narr", role="narration", params={"text": t})]


def fragment_to_bricks(plan: FragmentPlan, *, start: float = 0.0) -> list[ClipBrick]:
    """Le fragment (beats à effets) → une liste de `ClipBrick` v5, posés à la suite.

    `start` = décalage de départ sur la timeline (append derrière un fragment existant).
    """
    bricks: list[ClipBrick] = []
    cursor = start
    for i, beat in enumerate(plan.beats):
        bid = beat.id or f"{plan.part or 'part'}_{i}"
        dur = beat.duree_s if beat.duree_s > 0 else 3.0
        image = GenNode(params={"prompt": beat.sujet})
        shot = ShotBrief(sujet=beat.sujet, intention_plan=beat.narration_fr)
        nameplates = _nameplates(beat)
        placement = TimelinePlacement(start=cursor, duration=dur)
        if beat.kind == "video":
            brick = ClipBrick(
                id=bid, kind="video", image=image,
                motion=GenNode(params={"prompt": beat.sujet}), shot=shot,
                nameplates=nameplates, children=_narration(bid, beat.narration_fr),
                placement=placement,
            )
        elif beat.countdown:
            # Écran timer : effet IR, pas de narration (garde-fou du modèle).
            brick = ClipBrick(
                id=bid, kind="photo", image=image, shot=shot, countdown=CountdownSpec(),
                nameplates=nameplates, placement=placement,
            )
        else:
            brick = ClipBrick(
                id=bid, kind="photo", image=image, shot=shot,
                intro_eye_open=beat.eye_open, nameplates=nameplates,
                children=_narration(bid, beat.narration_fr), placement=placement,
            )
        bricks.append(brick)
        cursor += dur
    return bricks
