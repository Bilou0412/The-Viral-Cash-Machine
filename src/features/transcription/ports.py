from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class Cue:
    """A single subtitle with timing."""
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class Transcription:
    """Complete transcription as immutable tuple of cues."""
    cues: tuple[Cue, ...]

    def to_list(self) -> list[dict[str, Any]]:
        """Convert to list of dicts for backwards compat with metadata.json."""
        return [
            {"text": cue.text, "start": cue.start, "end": cue.end}
            for cue in self.cues
        ]


class Transcriber(Protocol):
    """Port for speech-to-text services."""

    def transcribe(self, audio_path: str) -> Transcription:
        """Transcribe audio file and return cues with timing."""
        ...
