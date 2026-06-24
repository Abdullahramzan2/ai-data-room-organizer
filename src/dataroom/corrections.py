"""Apply manual classification corrections from the review queue."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.export.review_queue import read_review_queue


def _normalize_path_key(path: str) -> str:
    return str(Path(path).resolve())


def load_corrections_from_review_queue(
    path: Path,
    *,
    column: str = "corrected_folder",
) -> dict[str, str]:
    """Read original_path -> taxonomy folder mappings from review_queue.xlsx."""
    if not path.is_file():
        return {}

    corrections: dict[str, str] = {}
    for row in read_review_queue(path):
        original = (row.get("original_path") or "").strip()
        folder = (row.get(column) or "").strip()
        if original and folder:
            corrections[_normalize_path_key(original)] = folder
    return corrections


def _category_for_folder(taxonomy: dict[str, Any], folder: str) -> tuple[str, str] | None:
    for cat in taxonomy.get("categories", []):
        if str(cat.get("folder", "")) == folder:
            return str(cat.get("id", "")), folder
    return None


def apply_corrections(
    classification_results: list[dict[str, Any]],
    corrections: dict[str, str],
    taxonomy: dict[str, Any],
) -> tuple[int, list[str]]:
    """
    Update classification rows in place from review-queue corrections.

    Returns (applied_count, warning messages for invalid folders).
    """
    if not corrections:
        return 0, []

    by_path = {_normalize_path_key(str(row["source_path"])): row for row in classification_results}
    applied = 0
    warnings: list[str] = []

    for original_path, folder in corrections.items():
        row = by_path.get(original_path)
        if row is None:
            warnings.append(f"No classification result for corrected file: {original_path}")
            continue

        resolved = _category_for_folder(taxonomy, folder)
        if resolved is None:
            warnings.append(f"Unknown taxonomy folder '{folder}' for {original_path}")
            continue

        category_id, category_folder = resolved
        row["category_id"] = category_id
        row["category_folder"] = category_folder
        row["needs_review"] = False
        row["review_reason"] = None
        row["method"] = "manual_correction"
        row["reason"] = f"Manual correction from review queue to {category_folder}"
        row["confidence"] = "high"
        row["classification_basis"] = f"manual_correction: {category_folder}"
        applied += 1

    return applied, warnings
