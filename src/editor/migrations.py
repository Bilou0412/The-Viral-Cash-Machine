"""Migrations forward-only du document éditeur (analogue de `_ensure_columns`).

`upgrade_document` prend un dict brut (chargé du JSON persisté) et le ramène au
`SCHEMA_VERSION` courant avant validation. Additif : on n'enlève jamais de champ.
"""

from typing import Any, Dict

from .document import SCHEMA_VERSION, EditorDocument


def upgrade_document(raw: Dict[str, Any]) -> EditorDocument:
    """Met à niveau un document brut puis le valide en `EditorDocument`."""
    data = dict(raw)
    version = int(data.get("schema_version", 1))

    # v1 → v2 : introduction de `ClipBrick` (briques composites VIDÉO/PHOTO).
    # Additif : les briques plates v1 (image/video/voice) restent VALIDES dans
    # l'union, donc rien à transformer ici — un doc v1 se charge tel quel sous v2.
    # Le repli briques-plates → ClipBrick interviendra avec B1 (quand `resolve.py`
    # et `editor_generation.py` consommeront les clips).
    _ = version

    data["schema_version"] = SCHEMA_VERSION
    return EditorDocument.model_validate(data)
