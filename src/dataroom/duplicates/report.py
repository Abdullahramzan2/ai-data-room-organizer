"""Build and write duplicate_report.xlsx."""

from __future__ import annotations

from pathlib import Path

from dataroom.duplicates.models import DuplicatePair
from dataroom.export.xlsx_io import write_table_xlsx

DUPLICATE_REPORT_COLUMNS = [
    "group_id",
    "duplicate_type",
    "file_a_path",
    "file_b_path",
    "file_a_hash",
    "file_b_hash",
    "similarity_score",
    "recommended_action",
]


def pairs_to_rows(pairs: list[DuplicatePair]) -> list[dict[str, str]]:
    return [
        {
            "group_id": pair.group_id,
            "duplicate_type": pair.duplicate_type,
            "file_a_path": pair.file_a_path,
            "file_b_path": pair.file_b_path,
            "file_a_hash": pair.file_a_hash,
            "file_b_hash": pair.file_b_hash,
            "similarity_score": str(pair.similarity_score),
            "recommended_action": pair.recommended_action,
        }
        for pair in pairs
    ]


def write_duplicate_report(path: Path, pairs: list[DuplicatePair]) -> None:
    write_table_xlsx(path, DUPLICATE_REPORT_COLUMNS, pairs_to_rows(pairs), sheet_title="Duplicates")


def write_duplicate_report_csv(path: Path, pairs: list[DuplicatePair]) -> None:
    write_duplicate_report(path, pairs)
