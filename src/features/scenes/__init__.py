"""Feature « scènes » : décrypteur de scènes (idée → VideoPlan) + builder vers
un `EditorDocument` (briques courtes + index de scènes). Chemin canonique neutre
qui remplace l'aventure CYOA pour le créateur de scènes."""

from .model import ScenePlan, ShotPlan, VideoPlan
from .ports import SceneDecompositionError, SceneVideoDecomposer
from .scene_plan_to_document import scene_plan_to_document

__all__ = [
    "SceneDecompositionError",
    "ScenePlan",
    "SceneVideoDecomposer",
    "ShotPlan",
    "VideoPlan",
    "scene_plan_to_document",
]
