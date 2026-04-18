from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.repository import RunRepository


@lru_cache(maxsize=1)
def get_repository() -> RunRepository:
    settings = get_settings()
    return RunRepository(settings.database_path)
