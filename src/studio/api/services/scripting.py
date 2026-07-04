"""Scripting service — pick the right AdventureDecomposer and run it.

Uses `OpenAIAdventureDecomposer` when an OpenAI key is configured, otherwise
falls back to the deterministic `FakeAdventureDecomposer` (offline dev + tests).
This keeps the route handler ignorant of provider selection.
"""

import os

from ....features.scripting.adventure import DEFAULT_ROUNDS, AdventureScript
from ....features.scripting.fake_adventure_decomposer import FakeAdventureDecomposer
from ....features.scripting.ports import AdventureDecomposer

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"


def get_decomposer(openai_key: str | None = None) -> AdventureDecomposer:
    """Return an OpenAI decomposer if a key is given, else the Fake one.

    ``openai_key`` = clé de l'utilisateur courant (B.2). Sans clé → décomposeur
    Fake déterministe (offline/tests).
    """
    if not openai_key:
        return FakeAdventureDecomposer()
    # Import lazily: the `openai` SDK is absent in offline/test environments.
    from openai import OpenAI

    from ....features.scripting.openai_adventure_decomposer import (
        OpenAIAdventureDecomposer,
    )

    model = os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    return OpenAIAdventureDecomposer(OpenAI(api_key=openai_key), model)


def generate_script(
    prompt: str,
    char_left_name: str,
    char_right_name: str,
    char_left_desc: str = "",
    char_right_desc: str = "",
    n_rounds: int = DEFAULT_ROUNDS,
    decomposer: AdventureDecomposer | None = None,
    openai_key: str | None = None,
) -> AdventureScript:
    """Generate a validated AdventureScript from the creator's inputs.

    Creator provides the adventure (prompt) + the 2 characters (name and,
    optionally, a description) + the number of choice-sequences (`n_rounds`).
    Empty descriptions are invented by the model.
    """
    dec = decomposer or get_decomposer(openai_key)
    return dec.decompose_adventure(
        prompt,
        char_left_name,
        char_right_name,
        char_left_desc,
        char_right_desc,
        n_rounds=n_rounds,
    )
