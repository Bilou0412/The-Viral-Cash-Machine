"""Migrations forward-only du document éditeur (analogue de `_ensure_columns`).

`upgrade_document` prend un dict brut (chargé du JSON persisté) et le ramène au
`SCHEMA_VERSION` courant avant validation. Additif jusqu'en v4 ; **v4 → v5** est
la 1re vraie transformation (le `shot` plat éclate sur les 3 niveaux).
"""

from typing import Any

from .compile_shot import recompile_document
from .document import SCHEMA_VERSION, EditorDocument


def _v4_to_v5(data: dict[str, Any]) -> None:
    """Éclate l'ancien `shot` plat (decor/lumiere/cadrage/characters/extra) sur les
    3 niveaux : le décor+lumière remontent en SCÈNE (via une `LocationEntry`
    synthétisée), le cadrage+personnages restent au PLAN.
    """
    bricks = data.get("bricks", []) or []
    scenes = data.get("scenes", []) or []
    by_id = {b.get("id"): b for b in bricks if isinstance(b, dict)}
    location_bible = data.setdefault("location_bible", [])

    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        # Décor/lumière de la scène = ceux de sa photo d'env (ou du 1er plan portant un shot).
        member_ids = [scene.get("environment_photo_ref", ""), *scene.get("shot_ids", [])]
        decor = lumiere = ""
        for mid in member_ids:
            old = (by_id.get(mid) or {}).get("shot") or {}
            decor = decor or old.get("decor", "")
            lumiere = lumiere or old.get("lumiere", "")
        if decor or lumiere:
            loc_ref = f"{scene.get('id', 'scene')}_loc"
            location_bible.append({"ref": loc_ref, "lieu": decor,
                                   "lumiere_base": {"sources": lumiere}})
            scene["location_ref"] = loc_ref
            scene.setdefault("lumiere_ambiante", {})["sources"] = lumiere

    for b in bricks:
        if not isinstance(b, dict):
            continue
        old = b.get("shot")
        if not isinstance(old, dict) or "cadre" in old:  # déjà v5 → laisser
            continue
        b["shot"] = {
            "cadre": {"taille_plan": old.get("cadrage", "")},
            "personnages_presents": [
                {"ref": c.get("ref", ""), "action": c.get("action", ""),
                 "expression": c.get("expression", "")}
                for c in old.get("characters", []) if isinstance(c, dict)
            ],
            "intention_plan": old.get("extra", ""),
        }


def upgrade_document(raw: dict[str, Any]) -> EditorDocument:
    """Met à niveau un document brut puis le valide en `EditorDocument`."""
    data = dict(raw)
    version = int(data.get("schema_version", 1))

    # v1→v2 (ClipBrick), v2→v3 (scenes), v3→v4 (shot/bible) : purement ADDITIFS —
    # un doc ancien se valide tel quel avec des défauts (rien à transformer).
    # v4 → v5 : architecture 3 niveaux (Vidéo→Scène→Plan) — le `shot` plat éclate.
    if version < 5:
        _v4_to_v5(data)

    data["schema_version"] = SCHEMA_VERSION
    doc = EditorDocument.model_validate(data)
    if version < 5:
        # Rafraîchit le cache des prompts vers la compilation v5 (héritage résolu).
        recompile_document(doc)
    return doc
