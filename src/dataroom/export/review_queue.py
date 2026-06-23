"""Write review_queue.csv for flagged documents."""

from __future__ import annotations

import csv
import math
import os
import tempfile
import time
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
    "corrected_folder",
]


class ReviewQueueWriteError(OSError):
    """Raised when review_queue.csv cannot be written (e.g. file locked on Windows)."""


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
                "corrected_folder": row.get("corrected_folder", ""),
            }
        )
    return review


def write_review_queue_csv(path: Path, manifest_rows: list[dict[str, str]]) -> None:
    write_review_queue_rows(path, build_review_rows(manifest_rows))


def read_review_queue_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            return []
        rows: list[dict[str, str]] = []
        for row in reader:
            normalized = {col: str(row.get(col, "") or "") for col in REVIEW_COLUMNS}
            rows.append(normalized)
        return rows


def _cell_str(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value)


def _normalize_review_rows(rows: list[dict[str, object]]) -> list[dict[str, str]]:
    return [{col: _cell_str(row.get(col)) for col in REVIEW_COLUMNS} for row in rows]


def _write_review_queue_atomic(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f"{path.stem}_",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=REVIEW_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def write_review_queue_rows(
    path: Path,
    rows: list[dict[str, object]],
    *,
    retries: int = 5,
) -> None:
    """Write review queue rows, retrying when the target file is locked (e.g. open in Excel)."""
    normalized = _normalize_review_rows(rows)
    last_error: PermissionError | None = None

    for attempt in range(retries):
        try:
            _write_review_queue_atomic(path, normalized)
            return
        except PermissionError as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(0.15 * (attempt + 1))

    raise ReviewQueueWriteError(
        f"Could not write {path}. Close review_queue.csv if it is open in Excel "
        "or another program, then try Save again."
    ) from last_error
