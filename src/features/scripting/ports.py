"""Script decomposition ports."""

from dataclasses import dataclass
from typing import Protocol


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
