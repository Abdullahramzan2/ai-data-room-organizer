"""Parse taxonomy YAML into classification categories."""

from __future__ import annotations

from typing import Any

from dataroom.classification.models import TaxonomyCategory


def parse_categories(taxonomy: dict[str, Any]) -> list[TaxonomyCategory]:
    categories: list[TaxonomyCategory] = []
    for raw in taxonomy.get("categories", []):
        categories.append(
            TaxonomyCategory(
                id=str(raw.get("id", "")),
                folder=str(raw.get("folder", "")),
                description=str(raw.get("description", "")).strip(),
                keywords=[str(k).lower() for k in raw.get("keywords", []) if k],
                exclude_if=[str(e).lower() for e in raw.get("exclude_if", []) if e],
                is_review_queue=bool(raw.get("is_review_queue", False)),
            )
        )
    return categories


def category_by_id(categories: list[TaxonomyCategory], category_id: str) -> TaxonomyCategory | None:
    for cat in categories:
        if cat.id == category_id:
            return cat
    return None


def review_queue_category(categories: list[TaxonomyCategory]) -> TaxonomyCategory:
    for cat in categories:
        if cat.is_review_queue:
            return cat
    return TaxonomyCategory(
        id="19",
        folder="19_Unclassified_Review_Queue",
        description="Unclassified review queue",
        is_review_queue=True,
    )


def classifiable_categories(categories: list[TaxonomyCategory]) -> list[TaxonomyCategory]:
    return [c for c in categories if not c.is_review_queue]
