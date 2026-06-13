"""Factory for reasoning provider selection."""

from __future__ import annotations

from typing import Any

from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.ollama_provider import OllamaReasoningProvider
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.settings import Settings, get_settings


def create_reasoning_provider(
    provider_name: str,
    settings: Settings | None = None,
) -> ReasoningProvider:
    """
    Select reasoning provider from config.

    Values: local | openai | ollama | auto
    """
    settings = settings or get_settings()
    name = (provider_name or "auto").strip().lower()

    if name == "local" or settings.classification_mode == "local":
        return LocalReasoningProvider()

    if name == "openai":
        return OpenAIReasoningProvider(settings)

    if name == "ollama":
        return OllamaReasoningProvider(settings)

    # auto: prefer OpenAI when key present, else Ollama if running, else local
    if settings.openai_api_key and settings.classification_mode in {"hybrid", "api"}:
        return OpenAIReasoningProvider(settings)

    ollama = OllamaReasoningProvider(settings)
    if ollama.is_available() and settings.classification_mode in {"hybrid", "api"}:
        return ollama

    return LocalReasoningProvider()
