"""Tests for review-queue correction loading and application."""

from __future__ import annotations

from pathlib import Path

from dataroom.corrections import apply_corrections, load_corrections_from_review_queue
from dataroom.config import load_taxonomy
from dataroom.export.review_queue import write_review_queue_rows


def test_load_corrections_from_review_queue(tmp_path: Path):
    review_path = tmp_path / "review_queue.xlsx"
    write_review_queue_rows(
        review_path,
        [
            {
                "file_name": "a.txt",
                "original_path": "C:/data/a.txt",
                "assigned_folder": "19_Unclassified",
                "confidence": "low",
                "score": "0.2",
                "review_reason": "uncertain",
                "classification_reason": "weak",
                "supporting_terms": "",
                "corrected_folder": "01_Project_Overview",
            },
            {
                "file_name": "b.txt",
                "original_path": "C:/data/b.txt",
                "assigned_folder": "19_Unclassified",
                "confidence": "low",
                "score": "0.2",
                "review_reason": "uncertain",
                "classification_reason": "weak",
                "supporting_terms": "",
                "corrected_folder": "",
            },
        ],
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
