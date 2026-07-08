"""Script decomposition feature.

Note: `OpenAIAdventureDecomposer` only references the `openai` SDK under
TYPE_CHECKING (the SDK is absent outside the container), so importing it here is
safe offline.
"""

from .adventure import (
    AdventureScript,
    Choice,
    Round,
    VoiceProfile,
    export_schema,
)
from .fake_adventure_decomposer import FakeAdventureDecomposer
from .openai_adventure_decomposer import OpenAIAdventureDecomposer
from .ports import AdventureDecomposer, ScriptDecomposer, ScriptDecomposition

__all__ = [
    "AdventureDecomposer",
    "AdventureScript",
    "Choice",
    "FakeAdventureDecomposer",
    "OpenAIAdventureDecomposer",
    "Round",
    "ScriptDecomposer",
    "ScriptDecomposition",
    "VoiceProfile",
    "export_schema",
]
