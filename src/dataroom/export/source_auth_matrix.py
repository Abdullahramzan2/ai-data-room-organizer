"""Source authentication matrix for folder 00 admin outputs."""

from __future__ import annotations

from pathlib import Path

from dataroom.export.xlsx_io import write_table_xlsx

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
    rows = build_source_authentication_rows(manifest_rows)
    write_table_xlsx(path, SOURCE_AUTH_COLUMNS, rows, sheet_title="Source Auth")
