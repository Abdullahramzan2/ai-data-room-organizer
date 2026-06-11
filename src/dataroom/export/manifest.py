"""Write manifest.csv for classified documents."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

MANIFEST_COLUMNS = [
    "file_name",
    "original_path",
    "output_path",
    "category_id",
    "category_folder",
    "confidence",
    "score",
    "classification_method",
    "classification_reason",
    "supporting_terms",
    "entities",
    "needs_review",
    "review_reason",
    "extraction_method",
    "char_count",
    "api_used",
]


def _join_list(values: list[str] | None) -> str:
    return "|".join(values or [])


def build_manifest_rows(
    ingestion_docs: list[dict[str, Any]],
    classification_results: list[dict[str, Any]],
    output_dir: Path | None = None,
    *,
    rename: bool = False,
) -> list[dict[str, str]]:
    """Merge ingestion + classification into manifest rows."""
    by_path = {row["source_path"]: row for row in classification_results}
    rows: list[dict[str, str]] = []

    for doc in ingestion_docs:
        source_path = doc["source_path"]
        cls = by_path.get(source_path)
        if cls is None:
            continue

        source = Path(source_path)
        output_path = ""
        if output_dir is not None:
            from dataroom.organizer.naming import build_dest_name

            dest_name = build_dest_name(
                source,
                str(cls["category_folder"]),
                rename=rename,
            )
            output_path = str(output_dir / cls["category_folder"] / dest_name)

        rows.append(
            {
                "file_name": doc["file_name"],
                "original_path": source_path,
                "output_path": output_path,
                "category_id": str(cls["category_id"]),
                "category_folder": str(cls["category_folder"]),
                "confidence": str(cls["confidence"]),
                "score": str(cls["score"]),
                "classification_method": str(cls["method"]),
                "classification_reason": str(cls.get("reason", "")),
                "supporting_terms": _join_list(cls.get("supporting_terms")),
                "entities": _join_list(cls.get("entities")),
                "needs_review": str(bool(cls.get("needs_review", False))).lower(),
                "review_reason": str(cls.get("review_reason") or ""),
                "extraction_method": str(doc.get("extraction_method", "")),
                "char_count": str(doc.get("char_count", 0)),
                "api_used": str(bool(cls.get("api_used", False))).lower(),
            }
        )

    return rows


def write_manifest_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
