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
    reasoning_provider: str = "auto"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"


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
    reasoning_provider = os.getenv("REASONING_PROVIDER", "auto").strip().lower() or "auto"
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip() or "http://localhost:11434"
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2").strip() or "llama3.2"
    return Settings(
        classification_mode=mode,
        reasoning_provider=reasoning_provider,
        openai_api_key=api_key,
        openai_model=model,
        ollama_base_url=ollama_url,
        ollama_model=ollama_model,
    )


def api_escalation_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        return False
    return settings.classification_mode in {"hybrid", "api"}
