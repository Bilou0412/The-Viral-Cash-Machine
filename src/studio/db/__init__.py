"""VCM Studio persistence: SQLModel models, engine, repositories, migration.

BLOBs (images/videos/audio) stay on disk under ``exports/``. The database only
stores metadata + local paths + Replicate prediction ids. RULE: never persist a
``replicate.delivery`` URL — those links expire.
"""

from src.studio.db.engine import init_db, get_session, get_engine
from src.studio.db.models import (
    Project,
    Episode,
    AdventureScriptRow,
    Asset,
    GenerationJob,
    VoiceProfile,
    CostEntry,
)

__all__ = [
    "init_db",
    "get_session",
    "get_engine",
    "Project",
    "Episode",
    "AdventureScriptRow",
    "Asset",
    "GenerationJob",
    "VoiceProfile",
    "CostEntry",
]
