"""Shared parsing of LLM classification JSON responses."""

from __future__ import annotations

import json

from dataroom.classification.models import TaxonomyCategory, TierResult
from dataroom.classification.providers.prompt import confidence_to_score


def parse_classification_data(
    data: dict,
    all_categories: list[TaxonomyCategory],
    *,
    method: str,
    default_reason: str,
) -> TierResult | None:
    """Map a parsed JSON object to a TierResult, or None if category_id is invalid."""
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
        method=method,
        supporting_terms=terms,
        reason=str(data.get("reason", default_reason)),
    )


def parse_classification_json(
    raw: str,
    all_categories: list[TaxonomyCategory],
    *,
    method: str,
    default_reason: str,
) -> TierResult | None:
    """Parse a JSON string from an LLM response into a TierResult."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return parse_classification_data(
        data,
        all_categories,
        method=method,
        default_reason=default_reason,
    )
