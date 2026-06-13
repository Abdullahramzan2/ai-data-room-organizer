"""Ollama local LLM reasoning provider."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.prompt import build_classification_prompt, confidence_to_score
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
        return False

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
                    {
                        "role": "system",
                        "content": (
                            "You classify documents for a legal/real-estate data room. "
                            "Respond with valid JSON only."
                        ),
                    },
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
            data = json.loads(raw)
        except Exception as exc:
            logger.warning("Ollama classification failed for %s: %s", file_name, exc)
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
            method="ollama",
            supporting_terms=terms,
            reason=str(data.get("reason", "Classified via Ollama")),
        )
