"""Feature FORMATS — le catalogue des moules vidéo (la couche « template »).

Import-light : juste des métadonnées de format. Le dispatcher (idée+format →
`EditorDocument`) vit au niveau service (`studio/api/services/formats.py`)."""

from .catalog import (
    DEFAULT_FORMAT,
    UnknownFormatError,
    VideoFormat,
    get_format,
    list_formats,
)

__all__ = [
    "DEFAULT_FORMAT",
    "UnknownFormatError",
    "VideoFormat",
    "get_format",
    "list_formats",
]
