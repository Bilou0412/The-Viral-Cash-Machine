"""Feature « scènes » : décrypteur de scènes (idée → VideoPlan) + builder vers
un `EditorDocument` (briques courtes + index de scènes). Chemin canonique neutre
qui remplace l'aventure CYOA pour le créateur de scènes."""

from .model import CharacterPlan, ScenePlan, ShotPlan, VideoPlan
from .ports import SceneDecompositionError, SceneVideoDecomposer
from .scene_plan_to_document import append_scene, scene_plan_to_document

__all__ = [
    "CharacterPlan",
    "SceneDecompositionError",
    "ScenePlan",
    "SceneVideoDecomposer",
    "ShotPlan",
    "VideoPlan",
    "append_scene",
    "scene_plan_to_document",
]
