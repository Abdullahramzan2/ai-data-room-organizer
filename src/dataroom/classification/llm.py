"""Tier 3: OpenAI LLM escalation for low-confidence documents."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult
from dataroom.settings import Settings

logger = logging.getLogger(__name__)


def _build_prompt(
    file_name: str,
    extension: str,
    excerpt: str,
    candidates: list[TaxonomyCategory],
) -> str:
    category_lines = []
    for cat in candidates:
        category_lines.append(
            f"- id={cat.id}, folder={cat.folder}, description={cat.description[:300]}"
        )
    categories_block = "\n".join(category_lines)
    return (
        "Classify this document into exactly one data room category.\n"
        "Return JSON only with keys: category_id, confidence, reason, "
        "supporting_terms, entities.\n"
        "confidence must be one of: high, medium, low.\n"
        "supporting_terms and entities must be arrays of strings.\n\n"
        f"File name: {file_name}\n"
        f"Extension: {extension}\n"
        f"Text excerpt:\n{excerpt}\n\n"
        f"Candidate categories:\n{categories_block}\n"
    )


def _confidence_to_score(confidence: str) -> float:
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(confidence.lower(), 0.3)


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
    if not settings.openai_api_key:
        return None

    excerpt = text[: config.llm_excerpt_chars].strip()
    if not excerpt:
        return None

    prompt = _build_prompt(file_name, extension, excerpt, candidates)

    try:
        if client is None:
            client = OpenAI(api_key=settings.openai_api_key)

        response = client.chat.completions.create(
            model=settings.openai_model,
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
        logger.warning("LLM classification failed for %s: %s", file_name, exc)
        return None

    category_id = str(data.get("category_id", "")).strip()
    cat = next((c for c in all_categories if c.id == category_id), None)
    if cat is None:
        return None

    confidence = str(data.get("confidence", "low")).lower()
    score = _confidence_to_score(confidence)
    terms = [str(t) for t in data.get("supporting_terms", []) if t]

    return TierResult(
        category_id=cat.id,
        category_folder=cat.folder,
        score=score,
        method="openai",
        supporting_terms=terms,
        reason=str(data.get("reason", "Classified via OpenAI API")),
    )
