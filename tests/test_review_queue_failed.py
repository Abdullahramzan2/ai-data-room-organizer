"""Tests for ingestion-failed files in the review queue."""

from __future__ import annotations

from pathlib import Path

from dataroom.export import build_manifest_rows, write_review_queue
from dataroom.export.review_queue import (
    build_ingestion_failed_review_rows,
    build_review_rows,
    read_review_queue,
)


def test_build_ingestion_failed_review_rows():
    failed = [
        (Path(r"C:\data\bad.pdf"), "parse error"),
        (Path(r"C:\data\worse.pdf"), "ocr timeout"),
    ]
    rows = build_ingestion_failed_review_rows(failed)
    assert len(rows) == 2
    assert rows[0]["file_name"] == "bad.pdf"
    assert rows[0]["confidence"] == "failed"
    assert rows[0]["assigned_folder"] == "19_Unclassified_Review_Queue"
    assert rows[0]["review_reason"] == "Ingestion failed: parse error"


def test_failed_files_included_in_review_queue(tmp_path: Path):
    ingestion_docs = [
        {
            "source_path": "C:/docs/ok.txt",
            "file_name": "ok.txt",
            "extraction_method": "native",
            "char_count": 100,
        }
    ]
    classification = [
        {
            "source_path": "C:/docs/ok.txt",
            "category_id": "19",
            "category_folder": "19_Unclassified_Review_Queue",
            "confidence": "low",
            "score": 0.2,
            "method": "embedding",
            "reason": "weak match",
            "supporting_terms": [],
            "entities": [],
            "needs_review": True,
            "review_reason": "Low confidence",
            "api_used": False,
        }
    ]
    failed = [(Path(r"C:\docs\bad.pdf"), "ingestion_failed: missing method")]

    manifest_rows = build_manifest_rows(ingestion_docs, classification, tmp_path / "out")
    review_rows = build_review_rows(manifest_rows, failed_files=failed)
    assert len(review_rows) == 2
    assert review_rows[1]["file_name"] == "bad.pdf"
    assert review_rows[1]["review_reason"].startswith("Ingestion failed:")

    review_path = tmp_path / "review_queue.xlsx"
    write_review_queue(review_path, manifest_rows, failed_files=failed)
    loaded = read_review_queue(review_path)
    assert len(loaded) == 2
    assert any(row["file_name"] == "bad.pdf" for row in loaded)
