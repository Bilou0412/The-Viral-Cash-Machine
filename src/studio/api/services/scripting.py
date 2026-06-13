"""Scripting service — pick the right AdventureDecomposer and run it.

Uses `OpenAIAdventureDecomposer` when an OpenAI key is configured, otherwise
falls back to the deterministic `FakeAdventureDecomposer` (offline dev + tests).
This keeps the route handler ignorant of provider selection.
"""

import os
from typing import Optional

from ....features.scripting.adventure import AdventureScript
from ....features.scripting.fake_adventure_decomposer import FakeAdventureDecomposer
from ....features.scripting.ports import AdventureDecomposer

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


def get_decomposer() -> AdventureDecomposer:
    """Return an OpenAI decomposer if a key is present, else the Fake one."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return FakeAdventureDecomposer()
    # Import lazily: the `openai` SDK is absent in offline/test environments.
    from openai import OpenAI

    from ....features.scripting.openai_adventure_decomposer import (
        OpenAIAdventureDecomposer,
    )

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIAdventureDecomposer(OpenAI(api_key=api_key), model)


def generate_script(
    prompt: str,
    char_left_name: str,
    char_right_name: str,
    decomposer: Optional[AdventureDecomposer] = None,
) -> AdventureScript:
    """Generate a validated AdventureScript from a prompt + character names."""
    dec = decomposer or get_decomposer()
    return dec.decompose_adventure(prompt, char_left_name, char_right_name)
