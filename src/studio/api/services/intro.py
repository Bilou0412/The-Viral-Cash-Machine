"""Génération de l'intro d'un épisode via le SYSTÈME EXISTANT.

Réutilise `Pipeline` (génération image-first) + `compositor.compose` (le montage
intro historique : eye-open → dialogue 2 persos → narration → timer « choisis ton
personnage », avec les PLAQUES DE NOMS). Les 2 personnages et le décor viennent
de l'`AdventureScript`. La narration utilise la voix conteur clonée (cohérence).

Sortie : un fichier intro final, enregistré comme Asset(beat="intro") de l'épisode.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.engine import Engine
from sqlmodel import Session

from ....features.scripting.adventure import AdventureScript
from ....features.scripting.prompts import DA, NO_TEXT, POV_HANDS, VERTICAL
from ....features.assets.replicate_provider import ReplicateAssetProvider
from ....infra.download import download_file
from ....pipeline import Pipeline, VideoInstance
from ...db.repositories import AssetRepo, EpisodeRepo, ProjectRepo
from .generation import _narrator_voice
from .paths import episode_dir


def _intro_image_prompt(script: AdventureScript) -> str:
    return (
        f"{VERTICAL} First-person POV horror. Two men stand facing us, full body, "
        f"at the mouth of a flooded mine. On the LEFT: {script.char_left_desc}. "
        f"On the RIGHT: {script.char_right_desc}. Both lit, facing the camera, "
        f"standing upright and still. {POV_HANDS}. {DA}. {NO_TEXT}"
    )


def _intro_video_prompt(script: AdventureScript) -> str:
    return (
        "Static locked-off camera, no camera movement. Two men face us in a "
        f"flooded mine. FIRST the LEFT man ({script.char_left_desc}) speaks "
        "straight to camera, pleading to be chosen; THEN the RIGHT man "
        f"({script.char_right_desc}) speaks straight to camera, threatening. "
        "Each leans SLOWLY toward the camera as he speaks but stays fully in "
        "frame, roots locked, no walking. Intense eye contact, full lip sync, "
        f"anguished. {POV_HANDS}. {DA}."
    )


def generate_intro(engine: Engine, episode_id: int) -> str:
    """Génère + compile l'intro de l'épisode ; renvoie le chemin du fichier final."""
    with Session(engine) as session:
        episode = EpisodeRepo(session).get(episode_id)
        if episode is None:
            raise ValueError(f"episode {episode_id} not found")
        project = ProjectRepo(session).get(episode.project_id)
        project_name = project.name if project else f"project_{episode.project_id}"
        from ...db.repositories import ScriptRepo

        row = ScriptRepo(session).latest_for_episode(episode_id)
        if row is None:
            raise ValueError("no script for episode")
        script = AdventureScript.model_validate_json(row.script_json)

    instance_id = f"episode_{episode_id}_intro"
    left, right = script.char_left_name, script.char_right_name
    # Les DEUX persos parlent (répliques d'intro R1 : chacun dit son nom, angoissant).
    speech = f"{script.char_left_intro_line_fr} {script.char_right_intro_line_fr}"
    # La narration conteur introduit le CARACTÈRE des deux + le choix.
    narration = (
        f"Voici {left}. {script.char_left_personality_fr} "
        f"Et voici {right}. {script.char_right_personality_fr} "
        f"Choisis ton compagnon pour la descente : {left}, ou {right}."
    )

    pipeline = Pipeline()
    # 1) Assets (image 2 persos -> dialogue ; voix perso + narrateur par défaut).
    pipeline.generate_assets(
        project_name,
        instance_id,
        _intro_video_prompt(script),
        _intro_image_prompt(script),
        speech,
        narration,
        video_type="intro",
    )

    # 2) Remplace la narration par la VOIX CONTEUR clonée (signature de la chaîne).
    base = os.environ.get("VCM_OUTPUT_DIR", "exports")
    inst_dir = os.path.join(base, project_name, instance_id)
    voice_id, model = _narrator_voice()
    narr_url = ReplicateAssetProvider().synthesize_voice(narration, voice_id, model)
    download_file(narr_url, inst_dir, "narrator.mp3")

    # 3) Détection des têtes + compile via le compositeur historique (nameplates+timer).
    heads = pipeline.detect_heads(project_name, instance_id)
    vi = VideoInstance(
        project_name=project_name,
        instance_id=instance_id,
        char_left_name=left,
        char_right_name=right,
        head_l_x=heads.left[0],
        head_l_y=heads.left[1],
        head_r_x=heads.right[0],
        head_r_y=heads.right[1],
    )
    compiled = pipeline.compile_video(vi)

    # 4) Enregistre l'intro comme asset de l'épisode (prepend au montage).
    with Session(engine) as session:
        AssetRepo(session).create(
            episode_id=episode_id,
            beat="intro",
            kind="video",
            round_index=None,
            prompt="(intro — système historique)",
            draft=False,
            status="ready",
            local_path=compiled.output_path,
        )
    return compiled.output_path
