"""Tier 3: OpenAI LLM escalation — delegates to OpenAIReasoningProvider."""

from __future__ import annotations

from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.settings import Settings


def classify_with_llm(
    file_name: str,
    extension: str,
    text: str,
    candidates: list[TaxonomyCategory],
    all_categories: list[TaxonomyCategory],
    config: ClassificationConfig,
    settings: Settings,
    *,
    client: Any | None = None,
) -> TierResult | None:
    """Backward-compatible wrapper around OpenAIReasoningProvider."""
    provider = OpenAIReasoningProvider(settings)
    return provider.classify(
        file_name,
        extension,
        text,
        candidates,
        all_categories,
        config,
        client=client,
    )
