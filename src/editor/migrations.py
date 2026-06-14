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

    # (futurs paliers : `if version < 2: ...` — transformations additives ici.)
    _ = version

    data["schema_version"] = SCHEMA_VERSION
    return EditorDocument.model_validate(data)
