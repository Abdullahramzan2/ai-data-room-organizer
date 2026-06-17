"""OpenAI reasoning provider."""

from __future__ import annotations

import logging
from typing import Any

from openai import OpenAI

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.prompt import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)
from dataroom.classification.providers.response import parse_classification_json
from dataroom.settings import Settings

logger = logging.getLogger(__name__)


class OpenAIReasoningProvider(ReasoningProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def provider_id(self) -> str:
        return "openai"

    @property
    def is_external(self) -> bool:
        return True

    def is_available(self) -> bool:
        return bool(self.settings.openai_api_key)

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
        if not self.is_available():
            return None

        excerpt = text[: config.llm_excerpt_chars].strip()
        if not excerpt:
            return None

        prompt = build_classification_prompt(file_name, extension, excerpt, candidates)

        try:
            if client is None:
                client = OpenAI(api_key=self.settings.openai_api_key)

            response = client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
        except Exception as exc:
            logger.warning("OpenAI classification failed for %s: %s", file_name, exc)
            return None

        return parse_classification_json(
            raw,
            all_categories,
            method="openai",
            default_reason="Classified via OpenAI API",
        )
