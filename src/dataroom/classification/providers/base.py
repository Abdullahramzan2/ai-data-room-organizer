"""Abstract reasoning provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult


class ReasoningProvider(ABC):
    """Model-agnostic interface for LLM/reasoning escalation (Tier 3)."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Stable identifier (e.g. openai, ollama, local)."""

    @property
    @abstractmethod
    def is_external(self) -> bool:
        """True when this provider sends data outside the local machine."""

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the provider can accept requests right now."""

    @abstractmethod
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
        """Classify using excerpt + metadata. Returns None if unavailable or failed."""
