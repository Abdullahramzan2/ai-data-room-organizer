"""Tests for review queue CSV read/write."""

from pathlib import Path

from dataroom.export.review_queue import (
    REVIEW_COLUMNS,
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
