"""Write review_queue.xlsx for flagged documents."""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from pathlib import Path

DEFAULT_REVIEW_FOLDER = "19_Unclassified_Review_Queue"

from dataroom.export.xlsx_io import (
    cell_str,
    normalize_rows,
    read_table_xlsx,
    write_table_xlsx_atomic,
)

REVIEW_COLUMNS = [
    "file_name",
    "original_path",
    "assigned_folder",
    "confidence",
    "score",
    "review_reason",
    "classification_reason",
    "supporting_terms",
    "corrected_folder",
]


class ReviewQueueWriteError(OSError):
    """Raised when review_queue.xlsx cannot be written (e.g. file locked on Windows)."""


def build_ingestion_failed_review_rows(
    failed_files: list[tuple[Path, str]],
    *,
    review_folder: str = DEFAULT_REVIEW_FOLDER,
) -> list[dict[str, str]]:
    """Build review-queue rows for files that failed during ingestion."""
    rows: list[dict[str, str]] = []
    for path, reason in failed_files:
        rows.append(
            {
                "file_name": path.name,
                "original_path": str(path),
                "assigned_folder": review_folder,
                "confidence": "failed",
                "score": "",
                "review_reason": f"Ingestion failed: {reason}",
                "classification_reason": "",
                "supporting_terms": "",
                "corrected_folder": "",
            }
        )
    return rows


def build_review_rows(
    manifest_rows: list[dict[str, str]],
    *,
    failed_files: list[tuple[Path, str]] | None = None,
    review_folder: str = DEFAULT_REVIEW_FOLDER,
) -> list[dict[str, str]]:
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
                "corrected_folder": row.get("corrected_folder", ""),
            }
        )
    if failed_files:
        review.extend(
            build_ingestion_failed_review_rows(failed_files, review_folder=review_folder)
        )
    return review


def write_review_queue(
    path: Path,
    manifest_rows: list[dict[str, str]],
    *,
    failed_files: list[tuple[Path, str]] | None = None,
    review_folder: str = DEFAULT_REVIEW_FOLDER,
) -> None:
    write_review_queue_rows(
        path,
        build_review_rows(
            manifest_rows,
            failed_files=failed_files,
            review_folder=review_folder,
        ),
    )


def read_review_queue(path: Path) -> list[dict[str, str]]:
    return read_table_xlsx(path, REVIEW_COLUMNS)


def write_review_queue_rows(
    path: Path,
    rows: Sequence[Mapping[str, object]],
    *,
    retries: int = 5,
) -> None:
    """Write review queue rows, retrying when the target file is locked (e.g. open in Excel)."""
    normalized = normalize_rows(rows, REVIEW_COLUMNS)
    last_error: PermissionError | None = None

    for attempt in range(retries):
        try:
            write_table_xlsx_atomic(
                path,
                REVIEW_COLUMNS,
                normalized,
                sheet_title="Review Queue",
            )
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))

    raise ReviewQueueWriteError(
        f"Could not write {path}. Close review_queue.xlsx if it is open in Excel "
        "or another program, then try Save again."
    ) from last_error


# Backward-compatible aliases (deprecated).
def write_review_queue_csv(path: Path, manifest_rows: list[dict[str, str]]) -> None:
    write_review_queue(path, manifest_rows)


def read_review_queue_csv(path: Path) -> list[dict[str, str]]:
    return read_review_queue(path)


def _cell_str(value: object) -> str:
    return cell_str(value)


def _normalize_review_rows(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return normalize_rows(rows, REVIEW_COLUMNS)
