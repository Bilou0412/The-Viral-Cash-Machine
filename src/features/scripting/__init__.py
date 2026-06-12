"""Script decomposition feature.

Note: the OpenAI-backed decomposers (`OpenAIScriptDecomposer`,
`OpenAIAdventureDecomposer`) are intentionally NOT re-exported here — they import
the `openai` SDK at module load, which is absent offline. Import them directly
from their module when needed. The Pydantic schema, ports and the Fake offline
decomposer stay importable without any network dependency.
"""

from .adventure import (
    AdventureScript,
    Choice,
    Round,
    VoiceProfile,
    export_schema,
)
from .fake_adventure_decomposer import FakeAdventureDecomposer
from .ports import AdventureDecomposer, ScriptDecomposer, ScriptDecomposition

__all__ = [
    "ScriptDecomposition",
    "ScriptDecomposer",
    "AdventureDecomposer",
    "AdventureScript",
    "Round",
    "Choice",
    "VoiceProfile",
    "export_schema",
    "FakeAdventureDecomposer",
]
