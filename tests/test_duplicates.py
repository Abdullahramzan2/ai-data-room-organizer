"""Tests for duplicate detection."""

import csv
from pathlib import Path

from dataroom.duplicates import (
    DuplicateConfig,
    detect_duplicates,
    write_duplicate_report_csv,
)
from dataroom.ingestion.hashing import sha256_file


def _doc(path: Path, text: str) -> dict:
    return {
        "source_path": str(path),
        "file_name": path.name,
        "extension": path.suffix,
        "file_size": path.stat().st_size,
        "file_hash": sha256_file(path),
        "combined_text": text,
        "text_content": text,
    }


def test_exact_duplicate_pair(tmp_path: Path):
    content = b"same bytes for exact duplicate test"
    a = tmp_path / "a.txt"
    b = tmp_path / "copy.txt"
    a.write_bytes(content)
    b.write_bytes(content)

    pairs = detect_duplicates([_doc(a, "hello"), _doc(b, "hello")], DuplicateConfig())
    assert len(pairs) == 1
    assert pairs[0].duplicate_type == "exact"
    assert pairs[0].similarity_score == 1.0
    assert pairs[0].recommended_action == "likely_duplicate"


def test_near_duplicate_pair(tmp_path: Path):
    a = tmp_path / "doc_a.txt"
    b = tmp_path / "doc_b.txt"
    text_a = (
        "This purchase and sale agreement covers land control, escrow, and closing "
        "conditions for the Big Pine development project in Bowie County."
    )
    text_b = (
        "This purchase and sale agreement covers land controls, escrow, and closing "
        "conditions for the Big Pine development project in Bowie County."
    )
    a.write_text(text_a, encoding="utf-8")
    b.write_text(text_b, encoding="utf-8")

    pairs = detect_duplicates(
        [_doc(a, text_a), _doc(b, text_b)],
        DuplicateConfig(near_similarity_threshold=0.9, min_text_chars_for_near=50),
    )
    near = [p for p in pairs if p.duplicate_type == "near"]
    assert len(near) == 1
    assert near[0].recommended_action in {"review", "likely_duplicate"}


def test_unrelated_files_no_duplicates(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("wetlands delineation report usace", encoding="utf-8")
    b.write_text("fiber telecom connectivity dark fiber", encoding="utf-8")

    pairs = detect_duplicates(
        [_doc(a, a.read_text(encoding="utf-8")), _doc(b, b.read_text(encoding="utf-8"))],
        DuplicateConfig(),
    )
    assert pairs == []


def test_duplicate_detection_disabled(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    pairs = detect_duplicates(
        [_doc(a, "x"), _doc(b, "x")],
        DuplicateConfig(enabled=False),
    )
    assert pairs == []


def test_write_duplicate_report_csv(tmp_path: Path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"same")
    b.write_bytes(b"same")
    pairs = detect_duplicates([_doc(a, "text"), _doc(b, "text")], DuplicateConfig())
    report_path = tmp_path / "duplicate_report.csv"
    write_duplicate_report_csv(report_path, pairs)

    with report_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 1
    assert rows[0]["duplicate_type"] == "exact"
    assert rows[0]["file_a_hash"] == rows[0]["file_b_hash"]
