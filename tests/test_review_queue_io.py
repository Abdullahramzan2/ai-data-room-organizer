"""Tests for review queue CSV read/write."""

from pathlib import Path
from unittest.mock import patch

import pytest

from dataroom.export.review_queue import (
    REVIEW_COLUMNS,
    ReviewQueueWriteError,
    read_review_queue_csv,
    write_review_queue_rows,
)


def test_review_queue_rows_round_trip(tmp_path: Path):
    rows = [
        {
            "file_name": "a.txt",
            "original_path": "C:/in/a.txt",
            "assigned_folder": "19_Unclassified_Review_Queue",
            "confidence": "low",
            "score": "0.3",
            "review_reason": "uncertain",
            "classification_reason": "weak keyword",
            "supporting_terms": "brac",
            "corrected_folder": "01_Project_Overview",
        }
    ]
    path = tmp_path / "review_queue.csv"
    write_review_queue_rows(path, rows)
    loaded = read_review_queue_csv(path)
    assert loaded == rows
    assert list(loaded[0].keys()) == REVIEW_COLUMNS


def test_write_review_queue_rows_normalizes_nan_corrected_folder(tmp_path: Path):
    path = tmp_path / "review_queue.csv"
    write_review_queue_rows(
        path,
        [
            {
                "file_name": "a.txt",
                "original_path": "C:/in/a.txt",
                "assigned_folder": "19_Unclassified_Review_Queue",
                "confidence": "low",
                "score": "0.3",
                "review_reason": "uncertain",
                "classification_reason": "weak keyword",
                "supporting_terms": "brac",
                "corrected_folder": float("nan"),
            }
        ],
    )
    loaded = read_review_queue_csv(path)
    assert loaded[0]["corrected_folder"] == ""


def test_write_review_queue_rows_raises_when_locked(tmp_path: Path):
    path = tmp_path / "review_queue.csv"
    path.write_text("locked", encoding="utf-8")

    def _always_denied(*_args, **_kwargs):
        raise PermissionError(13, "Permission denied")

    with patch("dataroom.export.review_queue._write_review_queue_atomic", side_effect=_always_denied):
        with pytest.raises(ReviewQueueWriteError, match="Close review_queue.csv"):
            write_review_queue_rows(path, [], retries=1)
