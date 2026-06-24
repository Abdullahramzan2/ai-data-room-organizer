"""Source authentication matrix for folder 00 admin outputs."""

from __future__ import annotations

import csv
from pathlib import Path

SOURCE_AUTH_COLUMNS = [
    "file_name",
    "original_path",
    "file_hash",
    "modified_at",
    "file_size",
    "extraction_method",
    "parse_status",
    "category_folder",
    "organize_status",
]


def build_source_authentication_rows(manifest_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """One row per file with integrity and provenance fields for diligence review."""
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        rows.append(
            {
                "file_name": row.get("file_name", ""),
                "original_path": row.get("original_path", ""),
                "file_hash": row.get("file_hash", ""),
                "modified_at": row.get("modified_at", ""),
                "file_size": row.get("file_size", ""),
                "extraction_method": row.get("extraction_method", ""),
                "parse_status": row.get("parse_status", ""),
                "category_folder": row.get("category_folder", ""),
                "organize_status": row.get("organize_status", ""),
            }
        )
    return rows


def write_source_authentication_matrix(path: Path, manifest_rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_source_authentication_rows(manifest_rows)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=SOURCE_AUTH_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
