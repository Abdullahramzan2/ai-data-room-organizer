"""Factory for reasoning provider selection."""

from __future__ import annotations

from dataroom.classification.mode import tier3_enabled
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.registry import (
    DEFAULT_AUTO_PROVIDER_CHAIN,
    DEFAULT_PROVIDER_REGISTRY,
    ProviderRegistry,
)
from dataroom.settings import Settings, get_settings


def create_reasoning_provider(
    provider_name: str,
    settings: Settings | None = None,
    *,
    auto_chain: list[str] | None = None,
    registry: ProviderRegistry | None = None,
) -> ReasoningProvider:
    """
    Select reasoning provider from config.

    Values: local | openai | ollama | enterprise | auto
    """
    settings = settings or get_settings()
    registry = registry or DEFAULT_PROVIDER_REGISTRY

    if not tier3_enabled(settings):
        return LocalReasoningProvider()

    name = (provider_name or "auto").strip().lower()
    if name == "local":
        return LocalReasoningProvider()

    chain = auto_chain or DEFAULT_AUTO_PROVIDER_CHAIN
    if name == "auto":
        return registry.resolve_auto(settings, chain)

    return registry.get(name, settings)
