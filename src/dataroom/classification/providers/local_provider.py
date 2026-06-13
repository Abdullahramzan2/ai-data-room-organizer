"""Local provider — keywords + embeddings only; no external escalation."""

from __future__ import annotations

from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider


class LocalReasoningProvider(ReasoningProvider):
    """Local-only provider; Tier 3 escalation is never performed."""

    @property
    def provider_id(self) -> str:
        return "local"

    @property
    def is_external(self) -> bool:
        return False

    def is_available(self) -> bool:
        return True

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
        return None
