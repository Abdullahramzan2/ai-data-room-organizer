"""Factory for reasoning provider selection."""

from __future__ import annotations

from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.enterprise_provider import EnterpriseReasoningProvider
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

    Values: local | openai | ollama | enterprise | auto
    """
    settings = settings or get_settings()
    name = (provider_name or "auto").strip().lower()

    if name == "local" or settings.classification_mode == "local":
        return LocalReasoningProvider()

    if name == "enterprise":
        return EnterpriseReasoningProvider(settings)

    if name == "openai":
        return OpenAIReasoningProvider(settings)

    if name == "ollama":
        return OllamaReasoningProvider(settings)

    # auto: enterprise (if configured), then OpenAI, then Ollama, else local
    if settings.classification_mode in {"hybrid", "api"}:
        enterprise = EnterpriseReasoningProvider(settings)
        if enterprise.is_available():
            return enterprise

        if settings.openai_api_key:
            return OpenAIReasoningProvider(settings)

        ollama = OllamaReasoningProvider(settings)
        if ollama.is_available():
            return ollama

    return LocalReasoningProvider()
