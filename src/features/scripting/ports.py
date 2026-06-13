"""Script decomposition ports."""

from dataclasses import dataclass
from typing import Protocol

from .adventure import AdventureScript


@dataclass(frozen=True)
class ScriptDecomposition:
    """Decomposed script elements for video instance."""

    monster_left_desc: str
    monster_right_desc: str
    monster_left_idle: str
    monster_right_idle: str
    environment_desc: str


class ScriptDecomposer(Protocol):
    """Port for decomposing user scripts into instance elements."""

    def decompose(self, script: str) -> ScriptDecomposition:
        """Decompose script into behavioral slots.

        Args:
            script: User-provided script description.

        Returns:
            ScriptDecomposition with filled visual slots.
        """
        ...


class AdventureDecomposer(Protocol):
    """Port for decomposing a user prompt into a full adventure script."""

    def decompose_adventure(
        self,
        prompt: str,
        char_left_name: str,
        char_right_name: str,
        char_left_desc: str = "",
        char_right_desc: str = "",
    ) -> AdventureScript:
        """Decompose a user prompt into a validated 3-round adventure script.

        Args:
            prompt: User-provided theme / pitch for the adventure (required).
            char_left_name: French first name of the left character (required).
            char_right_name: French first name of the right character (required).
            char_left_desc: OPTIONAL creator description of the left character
                (appearance + personality, FR or EN). If given, it is respected
                and adapted to the dark DA; if empty, the model invents it.
            char_right_desc: OPTIONAL creator description of the right character.

        Returns:
            A validated AdventureScript (3 rounds + epilogue, 2 character voices).
        """
        ...
