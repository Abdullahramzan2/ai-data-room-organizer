"""OpenAI reasoning provider."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.prompt import build_classification_prompt, confidence_to_score
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
                    {
                        "role": "system",
                        "content": (
                            "You classify documents for a legal/real-estate data room. "
                            "Respond with valid JSON only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
        except Exception as exc:
            logger.warning("OpenAI classification failed for %s: %s", file_name, exc)
            return None

        category_id = str(data.get("category_id", "")).strip()
        cat = next((c for c in all_categories if c.id == category_id), None)
        if cat is None:
            return None

        confidence = str(data.get("confidence", "low")).lower()
        terms = [str(t) for t in data.get("supporting_terms", []) if t]

        return TierResult(
            category_id=cat.id,
            category_folder=cat.folder,
            score=confidence_to_score(confidence),
            method="openai",
            supporting_terms=terms,
            reason=str(data.get("reason", "Classified via OpenAI API")),
        )
