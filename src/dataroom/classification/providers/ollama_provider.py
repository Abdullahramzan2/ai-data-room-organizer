"""Ollama local LLM reasoning provider."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.host_utils import is_trusted_local_host
from dataroom.classification.providers.prompt import (
    CLASSIFICATION_SYSTEM_PROMPT,
    build_classification_prompt,
)
from dataroom.classification.providers.response import parse_classification_json
from dataroom.settings import Settings

logger = logging.getLogger(__name__)


class OllamaReasoningProvider(ReasoningProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def provider_id(self) -> str:
        return "ollama"

    @property
    def is_external(self) -> bool:
        return not is_trusted_local_host(self.settings.ollama_base_url)

    def is_available(self) -> bool:
        return self._ping()

    def _ping(self) -> bool:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

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
            logger.info("Ollama not running at %s — skipping escalation", self.settings.ollama_base_url)
            return None

        excerpt = text[: config.llm_excerpt_chars].strip()
        if not excerpt:
            return None

        prompt = build_classification_prompt(file_name, extension, excerpt, candidates)
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = json.dumps(
            {
                "model": self.settings.ollama_model,
                "messages": [
                    {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": "json",
            }
        ).encode("utf-8")

        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            raw = body.get("message", {}).get("content", "{}")
        except Exception as exc:
            logger.warning("Ollama classification failed for %s: %s", file_name, exc)
            return None

        return parse_classification_json(
            raw,
            all_categories,
            method="ollama",
            default_reason="Classified via Ollama",
        )
