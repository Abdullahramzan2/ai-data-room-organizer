"""Shared prompt construction for reasoning providers."""

from __future__ import annotations

from dataroom.classification.models import TaxonomyCategory


def build_classification_prompt(
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


def confidence_to_score(confidence: str) -> float:
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3}
    return mapping.get(confidence.lower(), 0.3)
