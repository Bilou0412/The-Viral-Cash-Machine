"""Package éditeur (authoring timeline).

Imports légers uniquement (pydantic + videospec) : aucune dépendance réseau
(openai/replicate) au niveau module, pour que la collecte pytest fonctionne hors
conteneur. Les services réseau vivent dans `src/studio/api/services/`.
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
    "upgrade_document",
]
