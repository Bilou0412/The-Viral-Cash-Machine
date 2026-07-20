"""Dispatcher de FORMATS — idée + format → `EditorDocument`, un seul point d'entrée.

La couche « moule » (cf. `features/formats`) au niveau service : elle BINDE chaque
format du catalogue au pipeline existant qui l'incarne (décomposeur + adaptateur, tous
deux INCHANGÉS). Aujourd'hui deux pipelines symétriques — aventure (CYOA) et scènes —
qui retournent déjà le MÊME IR `EditorDocument`. On les unifie derrière un appel.

Le décomposeur n'improvise plus la FORME : le format la fixe, le décomposeur REMPLIT les
slots. Ceux-ci sont passés en `options` (bag volontairement souple) faute d'un schéma de
slots unifié — ce schéma viendra avec la passe de design au 3ᵉ format, PAS depuis n=1.
"""

from __future__ import annotations

from typing import Any

from ....editor.document import EditorDocument
from ....features.formats import UnknownFormatError, get_format
from ....features.scenes import scene_plan_to_document
from ....features.scenes.ports import DEFAULT_SCENES
from ....features.scripting.adventure import DEFAULT_ROUNDS
from ....features.scripting.adventure_to_video_plan import adventure_to_video_plan
from ....features.systems.ports import DEFAULT_STEPS
from .scenes import generate_video_plan
from .scripting import generate_script
from .systems import generate_system_plan


def build_format_document(
    format_id: str,
    prompt: str,
    *,
    title: str | None = None,
    openai_key: str | None = None,
    options: dict[str, Any] | None = None,
) -> EditorDocument:
    """Idée → `EditorDocument` selon le FORMAT choisi (un seul point d'entrée).

    `options` porte les slots PROPRES au format (persos pour l'aventure ; n_scenes/
    plateforme/langue pour les scènes) — souple tant qu'un schéma de slots unifié n'est
    pas conçu. `openai_key` absente → décomposeur Fake (offline). Lève `UnknownFormatError`
    pour un format hors catalogue.
    """
    fmt = get_format(format_id)   # valide l'id
    opts = options or {}
    if fmt.id == "aventure":
        script = generate_script(
            prompt,
            str(opts.get("char_left_name", "")),
            str(opts.get("char_right_name", "")),
            char_left_desc=str(opts.get("char_left_desc", "")),
            char_right_desc=str(opts.get("char_right_desc", "")),
            n_rounds=int(opts.get("n_rounds", DEFAULT_ROUNDS)),
            openai_key=openai_key,
        )
        # Rail UNIQUE (cf. .claude/rules/architecture.md) : le CYOA passe par v5 —
        # AdventureScript → VideoPlan → EditorDocument. Il hérite ainsi de compile_shot
        # (prompts courts), describe_document (texte) et document_to_spec, comme les scènes.
        plan = adventure_to_video_plan(script, side=str(opts.get("side", "left")))
        return scene_plan_to_document(plan, title=title or "Aventure")
    if fmt.id == "scenes":
        plan = generate_video_plan(
            prompt,
            style_identity=str(opts.get("style_identity", "")),
            n_scenes=int(opts.get("n_scenes", DEFAULT_SCENES)),
            platform=str(opts.get("platform", "tiktok")),
            language=str(opts.get("language", "fr")),
            target_duration_s=float(opts.get("target_duration_s", 0.0)),
            openai_key=openai_key,
        )
        return scene_plan_to_document(plan, title=title)
    if fmt.id == "systeme":
        # 1er argument = une IMAGE (dans les options) ; `prompt` sert d'indice texte.
        image = str(opts.get("image", ""))
        if not image:
            raise ValueError(
                "le format 'systeme' exige une image en entrée (options['image'] : "
                "URL, data-URI ou chemin)"
            )
        plan = generate_system_plan(
            image,
            hint=prompt,
            n_steps=int(opts.get("n_steps", DEFAULT_STEPS)),
            language=str(opts.get("language", "fr")),
            platform=str(opts.get("platform", "tiktok")),
            openai_key=openai_key,
        )
        return scene_plan_to_document(plan, title=title)
    # get_format garantit un id connu → cette branche est un garde-fou mort.
    raise UnknownFormatError(format_id)  # pragma: no cover
