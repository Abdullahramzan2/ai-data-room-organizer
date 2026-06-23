"""Tests for review-queue correction loading and application."""

from __future__ import annotations

import csv
from pathlib import Path

from dataroom.corrections import apply_corrections, load_corrections_from_review_queue
from dataroom.config import load_taxonomy


def test_load_corrections_from_review_queue(tmp_path: Path):
    review_path = tmp_path / "review_queue.csv"
    review_path.write_text(
        "file_name,original_path,assigned_folder,corrected_folder\n"
        "a.txt,C:/data/a.txt,19_Unclassified,01_Project_Overview\n"
        "b.txt,C:/data/b.txt,19_Unclassified,\n",
        encoding="utf-8",
    )

    corrections = load_corrections_from_review_queue(review_path)
    assert len(corrections) == 1
    assert "01_Project_Overview" in corrections.values()


def test_apply_corrections_updates_classification():
    taxonomy = load_taxonomy()
    results = [
        {
            "source_path": "C:/data/a.txt",
            "category_id": "19",
            "category_folder": "19_Unclassified_Review_Queue",
            "needs_review": True,
            "review_reason": "low confidence",
            "method": "keyword",
            "reason": "weak match",
            "confidence": "low",
            "score": 0.2,
        }
    ]
    corrections = {str(Path("C:/data/a.txt").resolve()): "01_Project_Overview"}

    applied, warnings = apply_corrections(results, corrections, taxonomy)
    assert applied == 1
    assert not warnings
    assert results[0]["category_folder"] == "01_Project_Overview"
    assert results[0]["category_id"] == "01"
    assert results[0]["needs_review"] is False
    assert results[0]["method"] == "manual_correction"


def test_apply_corrections_warns_on_unknown_folder():
    taxonomy = load_taxonomy()
    results = [{"source_path": "C:/data/a.txt", "category_folder": "19_Unclassified_Review_Queue"}]
    corrections = {str(Path("C:/data/a.txt").resolve()): "99_Not_A_Real_Folder"}

    applied, warnings = apply_corrections(results, corrections, taxonomy)
    assert applied == 0
    assert warnings
