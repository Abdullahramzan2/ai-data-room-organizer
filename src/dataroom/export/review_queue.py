"""Write review_queue.csv for flagged documents."""

from __future__ import annotations

import csv
from pathlib import Path

REVIEW_COLUMNS = [
    "file_name",
    "original_path",
    "assigned_folder",
    "confidence",
    "score",
    "review_reason",
    "classification_reason",
    "supporting_terms",
]


def build_review_rows(manifest_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    review: list[dict[str, str]] = []
    for row in manifest_rows:
        if row.get("needs_review") != "true":
            continue
        review.append(
            {
                "file_name": row["file_name"],
                "original_path": row["original_path"],
                "assigned_folder": row["category_folder"],
                "confidence": row["confidence"],
                "score": row["score"],
                "review_reason": row.get("needs_review_reason") or row.get("review_reason", ""),
                "classification_reason": row["classification_reason"],
                "supporting_terms": row["supporting_terms"],
            }
        )
    return review


def write_review_queue_csv(path: Path, manifest_rows: list[dict[str, str]]) -> None:
    rows = build_review_rows(manifest_rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
