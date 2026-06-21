"""Package éditeur (authoring timeline).

Imports légers uniquement (pydantic + videospec + `compositing.registry`, tous
sans dépendance réseau ni lourde) : aucun openai/replicate/moviepy au niveau
module, pour que la collecte pytest fonctionne hors conteneur. Les services
réseau vivent dans `src/studio/api/services/`.
"""

from .document import (
    SCHEMA_VERSION,
    AudioChild,
    Brick,
    ClipBrick,
    EditorDocument,
    GenerativeBrick,
    GenNode,
    Layer,
    MediaBrick,
    NarrativeContext,
    TextBrick,
    TimelinePlacement,
    Track,
    ZoomSpec,
)
from .compile_spec import document_to_spec
from .migrations import upgrade_document

__all__ = [
    "SCHEMA_VERSION",
    "AudioChild",
    "Brick",
    "ClipBrick",
    "EditorDocument",
    "GenerativeBrick",
    "GenNode",
    "Layer",
    "MediaBrick",
    "NarrativeContext",
    "TextBrick",
    "TimelinePlacement",
    "Track",
    "ZoomSpec",
    "document_to_spec",
    "upgrade_document",
]
