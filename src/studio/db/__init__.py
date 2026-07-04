"""VCM Studio persistence: SQLModel models, engine, repositories, migration.

BLOBs (images/videos/audio) stay on disk under ``exports/``. The database only
stores metadata + local paths + Replicate prediction ids. RULE: never persist a
``replicate.delivery`` URL — those links expire.
"""

from src.studio.db.engine import get_engine, get_session, init_db
from src.studio.db.models import (
    AdventureScriptRow,
    Asset,
    CostEntry,
    Episode,
    GenerationJob,
    Project,
    VoiceProfile,
)

__all__ = [
    "AdventureScriptRow",
    "Asset",
    "CostEntry",
    "Episode",
    "GenerationJob",
    "Project",
    "VoiceProfile",
    "get_engine",
    "get_session",
    "init_db",
]
