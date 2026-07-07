"""`VideoPlan` → `EditorDocument` (scènes + briques courtes) — adaptateur PUR.

Miroir neutre de `adventure_to_bricks`, mais piloté par le plan de scènes :
- pour chaque scène, une brique PHOTO d'environnement (contexte figé) ;
- puis un plan court = une brique VIDÉO/PHOTO (+ narration) qui l'animera ;
- l'index `document.Scene` référence ces briques par id (photo d'env + plans).

Durées/modèles paramétrés (défauts = ceux du rail). Aucune I/O, aucun réseau.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import cast

from ...editor.compile_shot import recompile_document
from ...editor.document import (
    AudioChild,
    Brick,
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    GenNode,
    NarrativeContext,
    Scene,
    ShotBrief,
    ShotCharacter,
    TimelinePlacement,
)
from ..assets.models import IMAGE_MODEL as _IMAGE_MODEL
from ..assets.models import VIDEO_MODEL as _VIDEO_MODEL
from ..assets.models import VOICE_MODEL as _VOICE_MODEL
from .model import CharacterPlan, ScenePlan, ShotPlan, VideoPlan

_DEFAULT_NARRATOR_VOICE = "Deep_Voice_Man"
_ENV_PHOTO_DUR = 3.0


def _slug(name: str) -> str:
    """Nom de personnage → id de bible stable (déterministe)."""
    s = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return s or "char"


def _build_bible(plan: VideoPlan) -> tuple[list[CharacterEntry], dict[str, str]]:
    """La bible (v4) depuis `plan.cast` + les persos cités dans les plans.

    Retourne (bible, name→id). Dédup par nom ; ids uniques. Si aucun cast/perso,
    bible vide (les plans resteront sans références → juste des blobs de décor).
    """
    name_to_id: dict[str, str] = {}
    entries: list[CharacterEntry] = []
    used: set[str] = set()

    def add(name: str, appearance: str, wardrobe: str, voice_id: str, traits: str) -> None:
        key = name.strip()
        if not key or key in name_to_id:
            return
        cid = _slug(key)
        while cid in used:
            cid += "_"
        used.add(cid)
        name_to_id[key] = cid
        entries.append(
            CharacterEntry(
                id=cid, name=key, appearance=appearance,
                wardrobe=wardrobe, voice_id=voice_id, traits=traits,
            )
        )

    for c in plan.cast:
        add(c.name, c.appearance, c.wardrobe, c.voice_id, c.traits)
    # Personnages cités dans les plans mais absents du cast → fiche minimale.
    for sp in plan.scenes:
        for shot in sp.shots:
            for sc in shot.characters:
                add(sc.name, sc.appearance, sc.wardrobe, "", "")
    return entries, name_to_id


def _shot_brief(shot: ShotPlan, name_to_id: dict[str, str]) -> ShotBrief | None:
    """Champs métier d'un plan, ou None si l'IA n'a rien émis de structuré (→ blob)."""
    people = [
        ShotCharacter(
            ref=name_to_id.get(sc.name.strip(), ""),
            name=sc.name,
            wardrobe=sc.wardrobe,
            expression=sc.expression,
            action=sc.action,
        )
        for sc in shot.characters
    ]
    if not (shot.decor or shot.lighting or shot.framing or people):
        return None
    return ShotBrief(
        decor=shot.decor, lumiere=shot.lighting, cadrage=shot.framing, characters=people
    )


def _env_brief(sp: ScenePlan) -> ShotBrief | None:
    """Le décor de la photo d'environnement (décor-led, sans sujet)."""
    if not (sp.environment_desc or sp.lighting):
        return None
    return ShotBrief(decor=sp.environment_desc, lumiere=sp.lighting)


def _scene_bricks(
    sp: ScenePlan,
    name_to_id: dict[str, str],
    place: Callable[[float], TimelinePlacement],
    narr_child: Callable[[str, str], list[AudioChild]],
    *,
    image_model: str,
    video_model: str,
    env_photo_dur: float,
) -> tuple[list[ClipBrick], Scene]:
    """Les briques + l'index d'UNE scène (photo d'env + plans). Réutilisé par le
    builder complet ET l'ajout incrémental (table ronde)."""
    out: list[ClipBrick] = []
    env_id = f"{sp.id}_env"
    out.append(
        ClipBrick(
            id=env_id, kind="photo",
            image=GenNode(model_ref=image_model, params={"prompt": sp.environment_desc}),
            shot=_env_brief(sp), children=[], placement=place(env_photo_dur),
        )
    )
    shot_ids = [env_id]
    env_ref = f"{{brick:{env_id}.image}}"
    for shot in sp.shots:
        children = narr_child(shot.id, shot.narration_fr)
        brief = _shot_brief(shot, name_to_id)
        if shot.kind == "video":
            brick = ClipBrick(
                id=shot.id, kind="video",
                image=GenNode(model_ref=image_model, params={"prompt": shot.visual_desc}),
                motion=GenNode(
                    model_ref=video_model,
                    params={"prompt": shot.motion_desc, "duration": shot.duration_s, "image": env_ref},
                ),
                shot=brief, children=children, placement=place(shot.duration_s),
            )
        else:
            brick = ClipBrick(
                id=shot.id, kind="photo",
                image=GenNode(model_ref=image_model, params={"prompt": shot.visual_desc}),
                shot=brief, children=children, placement=place(shot.duration_s),
            )
        out.append(brick)
        shot_ids.append(shot.id)
    scene = Scene(
        id=sp.id, title=sp.title,
        context=NarrativeContext(text=sp.context_text, art_direction=sp.art_direction),
        environment_photo_ref=env_id, shot_ids=shot_ids,
    )
    return out, scene


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

    bible, name_to_id = _build_bible(plan)
    bricks: list[ClipBrick] = []
    scenes: list[Scene] = []

    for sp in plan.scenes:
        clips, scene = _scene_bricks(
            sp, name_to_id, place, narr_child,
            image_model=image_model, video_model=video_model, env_photo_dur=env_photo_dur,
        )
        bricks.extend(clips)
        scenes.append(scene)

    context = NarrativeContext(
        text=plan.global_context,
        characters=plan.characters,
        art_direction=plan.art_direction,
    )
    doc = EditorDocument(
        title=title or plan.title,
        global_context=context,
        bricks=cast("list[Brick]", bricks),
        scenes=scenes,
        bible=bible,
    )
    # Champs métier = source de vérité → compile le prompt des briques `shot`.
    recompile_document(doc)
    return doc


def append_scene(
    doc: EditorDocument,
    sp: ScenePlan,
    new_characters: list[CharacterPlan],
    *,
    image_model: str = _IMAGE_MODEL,
    video_model: str = _VIDEO_MODEL,
    voice_model: str = _VOICE_MODEL,
    narrator_voice_id: str = _DEFAULT_NARRATOR_VOICE,
    env_photo_dur: float = _ENV_PHOTO_DUR,
) -> None:
    """Ajoute UNE scène (issue de la table ronde) à un document existant.

    Fusionne les nouveaux personnages dans la bible (dédup, ids uniques), place la
    scène après ce qui existe sur la timeline, puis recompile les prompts. Mute
    `doc` en place (la mémoire/continuité vit hors d'ici, dans le service)."""
    used_ids = {c.id for c in doc.bible}
    name_to_id = {c.name: c.id for c in doc.bible if c.name}

    def _ensure(name: str, appearance: str, wardrobe: str, voice_id: str, traits: str) -> None:
        key = name.strip()
        if not key or key in name_to_id:
            return
        cid = _slug(key)
        while cid in used_ids:
            cid += "_"
        used_ids.add(cid)
        name_to_id[key] = cid
        doc.bible.append(
            CharacterEntry(id=cid, name=key, appearance=appearance,
                           wardrobe=wardrobe, voice_id=voice_id, traits=traits)
        )

    for c in new_characters:
        _ensure(c.name, c.appearance, c.wardrobe, c.voice_id, c.traits)
    for shot in sp.shots:  # persos cités dans les plans mais absents de la bible
        for scp in shot.characters:
            _ensure(scp.name, scp.appearance, scp.wardrobe, "", "")

    cursor = max(
        (b.placement.start + b.placement.duration
         for b in doc.bricks if isinstance(b, ClipBrick)),
        default=0.0,
    )

    def place(duration: float) -> TimelinePlacement:
        nonlocal cursor
        pl = TimelinePlacement(track=0, start=cursor, duration=duration)
        cursor += duration
        return pl

    def narr_child(brick_id: str, text: str) -> list[AudioChild]:
        if not text:
            return []
        return [
            AudioChild(id=f"{brick_id}__narr", role="narration",
                       model_ref=voice_model, params={"text": text, "voice_id": narrator_voice_id})
        ]

    clips, scene = _scene_bricks(
        sp, name_to_id, place, narr_child,
        image_model=image_model, video_model=video_model, env_photo_dur=env_photo_dur,
    )
    doc.bricks.extend(cast("list[Brick]", clips))
    doc.scenes.append(scene)
    recompile_document(doc)
