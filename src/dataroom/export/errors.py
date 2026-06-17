"""Write errors_report.csv for skipped, failed, and organize errors."""

from __future__ import annotations

import csv
from pathlib import Path

from dataroom.organizer.models import OrganizeResult

ERROR_REPORT_COLUMNS = ["file_name", "original_path", "stage", "reason"]


def build_ingestion_error_rows(
    skipped_files: list[Path],
    failed_files: list[tuple[Path, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in skipped_files:
        rows.append(
            {
                "file_name": path.name,
                "original_path": str(path),
                "stage": "ingestion_skipped",
                "reason": "Skipped during ingestion (unsupported type or size limit)",
            }
        )
    for path, reason in failed_files:
        rows.append(
            {
                "file_name": path.name,
                "original_path": str(path),
                "stage": "ingestion_failed",
                "reason": reason,
            }
        )
    return rows


def build_organize_error_rows(results: list[OrganizeResult]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for result in results:
        if result.success:
            continue
        rows.append(
            {
                "file_name": result.source_path.name,
                "original_path": str(result.source_path),
                "stage": "organize_failed",
                "reason": result.error or "Organize failed",
            }
        )
    return rows


def write_errors_report_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=ERROR_REPORT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
