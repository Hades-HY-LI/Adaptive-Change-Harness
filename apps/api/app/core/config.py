from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os
from typing import Optional


ROOT_DIR = Path(__file__).resolve().parents[4]
ENV_PATHS = (
    ROOT_DIR / ".env",
    ROOT_DIR / "apps" / "api" / ".env",
)


@dataclass
class Settings:
    app_name: str = "Adaptive Change Harness API"
    api_prefix: str = "/api/v1"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)
    artifact_root: Path = ROOT_DIR / "artifacts"
    demo_repo_root: Path = ROOT_DIR / "demo-repo"
    skill_assets_root: Path = ROOT_DIR / "skill_assets"
    database_path: Path = ROOT_DIR / "artifacts" / "harness.sqlite3"
    fake_provider_enabled: bool = False
    fake_model: str = "deterministic-repair-v1"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5"
    request_timeout_seconds: int = 45


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_env_files()
    cors = tuple(
        part.strip()
        for part in os.getenv("CORS_ORIGIN", "http://localhost:5173").split(",")
        if part.strip()
    )
    artifact_root = Path(os.getenv("ARTIFACT_ROOT", ROOT_DIR / "artifacts")).resolve()
    database_path = Path(os.getenv("DATABASE_PATH", artifact_root / "harness.sqlite3")).resolve()
    demo_repo_root = Path(os.getenv("DEMO_REPO_ROOT", ROOT_DIR / "demo-repo")).resolve()
    skill_assets_root = Path(os.getenv("SKILL_ASSETS_ROOT", ROOT_DIR / "skill_assets")).resolve()
    return Settings(
        cors_origins=cors or ("http://localhost:5173",),
        artifact_root=artifact_root,
        database_path=database_path,
        demo_repo_root=demo_repo_root,
        skill_assets_root=skill_assets_root,
        fake_provider_enabled=_env_flag("FAKE_PROVIDER_ENABLED"),
        fake_model=os.getenv("FAKE_MODEL", "deterministic-repair-v1"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-5"),
        request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "45")),
    )


def _load_env_files() -> None:
    for env_path in ENV_PATHS:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}
