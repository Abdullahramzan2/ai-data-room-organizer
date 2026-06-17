"""Tests for provider registry."""

from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.classification.providers.registry import (
    DEFAULT_AUTO_PROVIDER_CHAIN,
    ProviderRegistry,
    ProviderSpec,
    build_default_registry,
)
from dataroom.settings import Settings


def test_default_registry_known_providers():
    registry = build_default_registry()
    assert registry.known_providers() == ["enterprise", "ollama", "openai"]


def test_registry_get_openai():
    registry = build_default_registry()
    provider = registry.get(
        "openai",
        Settings(classification_mode="hybrid", openai_api_key="sk-test"),
    )
    assert isinstance(provider, OpenAIReasoningProvider)


def test_registry_resolve_auto_custom_chain():
    registry = ProviderRegistry()
    registry.register(ProviderSpec("openai", OpenAIReasoningProvider))
    provider = registry.resolve_auto(
        Settings(classification_mode="hybrid", openai_api_key="sk-test"),
        ["openai", "local"],
    )
    assert isinstance(provider, OpenAIReasoningProvider)


def test_registry_resolve_auto_falls_back_to_local():
    registry = build_default_registry()
    provider = registry.resolve_auto(
        Settings(classification_mode="hybrid"),
        DEFAULT_AUTO_PROVIDER_CHAIN,
    )
    assert isinstance(provider, LocalReasoningProvider)
