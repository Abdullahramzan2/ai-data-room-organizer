"""Tier 1: taxonomy keyword matching."""

from __future__ import annotations

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult


def _is_excluded(category: TaxonomyCategory, haystack: str) -> bool:
    for phrase in category.exclude_if:
        if phrase and phrase in haystack:
            return True
    return False


def score_category_keywords(
    category: TaxonomyCategory,
    file_name: str,
    text: str,
) -> tuple[float, list[str]]:
    if not category.keywords:
        return 0.0, []

    haystack = f"{file_name} {text}".lower()
    if _is_excluded(category, haystack):
        return 0.0, []

    matched: list[str] = []
    for keyword in category.keywords:
        if keyword in haystack:
            matched.append(keyword)

    if not matched:
        return 0.0, []

    # Score relative to keyword list size, capped at 1.0
    score = min(1.0, len(matched) / max(1, min(len(category.keywords), 5)))
    # Boost when keyword appears in file name
    name_lower = file_name.lower()
    if any(kw in name_lower for kw in matched):
        score = min(1.0, score + 0.15)
    return score, matched


def classify_by_keywords(
    categories: list[TaxonomyCategory],
    file_name: str,
    text: str,
    config: ClassificationConfig,
) -> TierResult | None:
    best_score = 0.0
    best_cat: TaxonomyCategory | None = None
    best_terms: list[str] = []

    for category in categories:
        score, terms = score_category_keywords(category, file_name, text)
        if score > best_score:
            best_score = score
            best_cat = category
            best_terms = terms

    if best_cat is None or best_score <= 0:
        return None

    return TierResult(
        category_id=best_cat.id,
        category_folder=best_cat.folder,
        score=best_score,
        method="keyword",
        supporting_terms=best_terms,
        reason=f"Matched keywords: {', '.join(best_terms[:5])}",
    )
