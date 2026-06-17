"""Registry for reasoning provider registration and auto-selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.enterprise_provider import EnterpriseReasoningProvider
from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.ollama_provider import OllamaReasoningProvider
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.settings import Settings

ProviderFactory = Callable[[Settings], ReasoningProvider]

DEFAULT_AUTO_PROVIDER_CHAIN = ["enterprise", "openai", "ollama", "local"]


@dataclass(frozen=True)
class ProviderSpec:
    provider_id: str
    factory: ProviderFactory


class ProviderRegistry:
    """Register and resolve reasoning providers by id."""

    def __init__(self) -> None:
        self._specs: dict[str, ProviderSpec] = {}

    def register(self, spec: ProviderSpec) -> None:
        self._specs[spec.provider_id] = spec

    def known_providers(self) -> list[str]:
        return sorted(self._specs.keys())

    def get(self, provider_id: str, settings: Settings) -> ReasoningProvider:
        spec = self._specs.get(provider_id)
        if spec is None:
            raise ValueError(f"Unknown reasoning provider: {provider_id}")
        return spec.factory(settings)

    def resolve_auto(self, settings: Settings, chain: list[str]) -> ReasoningProvider:
        """Pick the first available provider in chain order."""
        for entry in chain:
            name = entry.strip().lower()
            if not name or name == "local":
                return LocalReasoningProvider()
            spec = self._specs.get(name)
            if spec is None:
                continue
            provider = spec.factory(settings)
            if provider.is_available():
                return provider
        return LocalReasoningProvider()


def build_default_registry() -> ProviderRegistry:
    registry = ProviderRegistry()
    registry.register(ProviderSpec("enterprise", EnterpriseReasoningProvider))
    registry.register(ProviderSpec("openai", OpenAIReasoningProvider))
    registry.register(ProviderSpec("ollama", OllamaReasoningProvider))
    return registry


DEFAULT_PROVIDER_REGISTRY = build_default_registry()
