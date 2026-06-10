"""Environment-backed settings (FastAPI-style .env loading)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

from dataroom.config import resolve_project_root


@dataclass(frozen=True)
class Settings:
    classification_mode: str = "hybrid"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"


def _load_dotenv() -> None:
    root = resolve_project_root()
    env_path = root / ".env"
    if env_path.is_file():
        load_dotenv(env_path)


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    mode = os.getenv("CLASSIFICATION_MODE", "hybrid").strip().lower()
    if mode not in {"local", "hybrid", "api"}:
        mode = "hybrid"
    api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    return Settings(
        classification_mode=mode,
        openai_api_key=api_key,
        openai_model=model,
    )


def api_escalation_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        return False
    return settings.classification_mode in {"hybrid", "api"}
