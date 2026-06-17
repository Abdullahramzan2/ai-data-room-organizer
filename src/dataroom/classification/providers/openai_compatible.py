"""OpenAI-compatible chat-completions provider for enterprise and cloud LLM gateways."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.host_utils import is_trusted_local_host
from dataroom.classification.providers.prompt import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)
from dataroom.classification.providers.response import parse_classification_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    """Connection settings for an OpenAI-compatible chat API."""

    provider_id: str
    api_key: str | None
    model: str
    base_url: str | None = None
    timeout: float = 120.0
    extra_headers: dict[str, str] = field(default_factory=dict)
    default_reason: str = "Classified via OpenAI-compatible API"
    force_external: bool | None = None


class OpenAICompatibleProvider(ReasoningProvider):
    """Reasoning provider using the OpenAI Python SDK against any compatible endpoint."""

    def __init__(self, config: OpenAICompatibleConfig):
        self._config = config

    @property
    def provider_id(self) -> str:
        return self._config.provider_id

    @property
    def is_external(self) -> bool:
        if self._config.force_external is not None:
            return self._config.force_external
        if not self._config.base_url:
            return True
        return not is_trusted_local_host(self._config.base_url)

    def is_available(self) -> bool:
        if not self._config.api_key or not self._config.model:
            return False
        if self._config.provider_id != "openai" and not self._config.base_url:
            return False
        return True

    def _build_client(self) -> OpenAI:
        kwargs: dict[str, Any] = {
            "api_key": self._config.api_key,
            "timeout": self._config.timeout,
        }
        if self._config.base_url:
            kwargs["base_url"] = self._config.base_url
        if self._config.extra_headers:
            kwargs["default_headers"] = self._config.extra_headers
        return OpenAI(**kwargs)

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
                client = self._build_client()

            request_kwargs: dict[str, Any] = {
                "model": self._config.model,
                "messages": [
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
                "response_format": {"type": "json_object"},
            }

            response = client.chat.completions.create(**request_kwargs)
            raw = response.choices[0].message.content or "{}"
        except Exception as exc:
            logger.warning(
                "%s classification failed for %s: %s",
                self._config.provider_id,
                file_name,
                exc,
            )
            return None

        return parse_classification_json(
            raw,
            all_categories,
            method=self._config.provider_id,
            default_reason=self._config.default_reason,
        )
