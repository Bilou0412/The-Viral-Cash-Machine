"""Package éditeur (authoring timeline).

Imports légers uniquement (pydantic + videospec + `compositing.registry`, tous
sans dépendance réseau ni lourde) : aucun openai/replicate/moviepy au niveau
module, pour que la collecte pytest fonctionne hors conteneur. Les services
réseau vivent dans `src/studio/api/services/`.
"""

from .compile_shot import compile_shot_prompt, recompile_document
from .compile_spec import document_to_spec
from .document import (
    SCHEMA_VERSION,
    AudioChild,
    Brick,
    CharacterEntry,
    ClipBrick,
    EditorDocument,
    GenerativeBrick,
    GenNode,
    Layer,
    MediaBrick,
    NarrativeContext,
    Scene,
    ShotBrief,
    ShotCharacter,
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
    "CharacterEntry",
    "ClipBrick",
    "EditorDocument",
    "GenNode",
    "GenerativeBrick",
    "Layer",
    "MediaBrick",
    "NarrativeContext",
    "Scene",
    "ShotBrief",
    "ShotCharacter",
    "TextBrick",
    "TimelinePlacement",
    "Track",
    "ZoomSpec",
    "compile_shot_prompt",
    "document_to_spec",
    "recompile_document",
    "upgrade_document",
]
