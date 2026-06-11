"""Tier 1: taxonomy keyword matching."""

from __future__ import annotations

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult

# Strong filename signals even when the keyword is a short acronym
_FILENAME_ACRONYM_BOOST = frozenset({"esa", "brac", "rcra", "foset", "fost", "tceq", "usace"})

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
    # Boost when keyword appears in file name (strong signal in data rooms)
    name_lower = file_name.lower()
    name_matched = [kw for kw in matched if kw in name_lower]
    if name_matched:
        score = min(1.0, score + 0.15)
        if len(name_matched) >= 2 or any(len(kw) >= 4 for kw in name_matched):
            score = max(score, 0.55)
        elif any(kw in _FILENAME_ACRONYM_BOOST for kw in name_matched):
            score = max(score, 0.55)
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
