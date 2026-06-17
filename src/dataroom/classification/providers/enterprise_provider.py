"""Enterprise / private LLM reasoning provider (OpenAI-compatible API)."""

from __future__ import annotations

from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from dataroom.settings import Settings


def enterprise_compatible_config(settings: Settings) -> OpenAICompatibleConfig:
    return OpenAICompatibleConfig(
        provider_id="enterprise",
        api_key=settings.enterprise_api_key,
        base_url=settings.enterprise_base_url,
        model=settings.enterprise_model,
        timeout=settings.enterprise_timeout,
        extra_headers=settings.enterprise_extra_headers,
        default_reason="Classified via enterprise LLM",
    )


class EnterpriseReasoningProvider(ReasoningProvider):
    """Aleph Alpha, vLLM, Azure OpenAI, and other OpenAI-compatible enterprise endpoints."""

    def __init__(self, settings: Settings):
        self._inner = OpenAICompatibleProvider(enterprise_compatible_config(settings))

    @property
    def provider_id(self) -> str:
        return self._inner.provider_id

    @property
    def is_external(self) -> bool:
        return self._inner.is_external

    def is_available(self) -> bool:
        return self._inner.is_available()

    def classify(
        self,
        file_name: str,
        extension: str,
        text: str,
        candidates: list[TaxonomyCategory],
        all_categories: list[TaxonomyCategory],
        config: ClassificationConfig,
        *,
        client: Any | None = None,
    ) -> TierResult | None:
        return self._inner.classify(
            file_name,
            extension,
            text,
            candidates,
            all_categories,
            config,
            client=client,
        )
