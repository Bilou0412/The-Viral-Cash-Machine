"""Export du JSON Schema de VideoSpec.

Le schéma sert de contrainte au structured output LLM (phase Plan) :
le modèle ne peut produire qu'un VideoSpec valide.

Usage : python -m src.videospec.schema [chemin/sortie.json]
"""

import json
import sys
from pathlib import Path

from .models import VideoSpec

DEFAULT_PATH = "schemas/videospec.schema.json"


def export_schema(path: str = DEFAULT_PATH) -> str:
    """Écrit le JSON Schema de VideoSpec et retourne le chemin."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = VideoSpec.model_json_schema()
    out.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    print(export_schema(target))
