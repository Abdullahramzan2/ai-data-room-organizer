"""Environment-backed settings (FastAPI-style .env loading)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
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
    enterprise_api_key: str | None = None
    enterprise_base_url: str | None = None
    enterprise_model: str = ""
    enterprise_timeout: float = 120.0
    enterprise_extra_headers: dict[str, str] = field(default_factory=dict)


def _parse_extra_headers(raw: str) -> dict[str, str]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(value) for key, value in parsed.items()}


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
    enterprise_key = os.getenv("ENTERPRISE_API_KEY", "").strip() or None
    enterprise_url = os.getenv("ENTERPRISE_BASE_URL", "").strip() or None
    enterprise_model = os.getenv("ENTERPRISE_MODEL", "").strip()
    try:
        enterprise_timeout = float(os.getenv("ENTERPRISE_TIMEOUT", "120").strip() or "120")
    except ValueError:
        enterprise_timeout = 120.0
    enterprise_headers = _parse_extra_headers(os.getenv("ENTERPRISE_EXTRA_HEADERS", ""))
    return Settings(
        classification_mode=mode,
        reasoning_provider=reasoning_provider,
        openai_api_key=api_key,
        openai_model=model,
        ollama_base_url=ollama_url,
        ollama_model=ollama_model,
        enterprise_api_key=enterprise_key,
        enterprise_base_url=enterprise_url,
        enterprise_model=enterprise_model,
        enterprise_timeout=enterprise_timeout,
        enterprise_extra_headers=enterprise_headers,
    )


def api_escalation_enabled(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if settings.classification_mode not in {"hybrid", "api"}:
        return False
    if settings.openai_api_key or settings.enterprise_api_key:
        return True
    return False
