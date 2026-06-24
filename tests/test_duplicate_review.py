"""Tests for duplicate-pair review flagging."""

from pathlib import Path

from dataroom.duplicates.models import DuplicatePair
from dataroom.duplicates.review_flags import apply_duplicate_review_flags
from dataroom.export import build_manifest_rows, write_review_queue
from dataroom.export.review_queue import read_review_queue


def _pair(file_a: Path, file_b: Path, *, duplicate_type: str = "exact") -> DuplicatePair:
    return DuplicatePair(
        group_id="g1",
        duplicate_type=duplicate_type,
        file_a_path=str(file_a),
        file_b_path=str(file_b),
        file_a_hash="h1",
        file_b_hash="h1" if duplicate_type == "exact" else "h2",
        similarity_score=1.0 if duplicate_type == "exact" else 0.92,
        recommended_action="likely_duplicate" if duplicate_type == "exact" else "review",
    )


def test_apply_duplicate_review_flags_both_files(tmp_path: Path):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    classification = [
        {"source_path": str(file_a), "needs_review": False, "review_reason": None},
        {"source_path": str(file_b), "needs_review": False, "review_reason": None},
    ]

    flagged = apply_duplicate_review_flags(classification, [_pair(file_a, file_b)])

    assert flagged == 2
    for row in classification:
        assert row["needs_review"] is True
        assert "Duplicate:" in row["review_reason"]
        assert "exact duplicate" in row["review_reason"].lower()


def test_apply_duplicate_review_flags_preserves_existing_reason(tmp_path: Path):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    classification = [
        {
            "source_path": str(file_a),
            "needs_review": True,
            "review_reason": "Low confidence",
        },
    ]

    apply_duplicate_review_flags(classification, [_pair(file_a, file_b)])

    assert classification[0]["review_reason"].startswith("Low confidence | Duplicate:")


def test_apply_duplicate_review_flags_respects_disabled(tmp_path: Path):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    classification = [{"source_path": str(file_a), "needs_review": False, "review_reason": None}]

    flagged = apply_duplicate_review_flags(
        classification,
        [_pair(file_a, file_b)],
        flag_for_review=False,
    )

    assert flagged == 0
    assert classification[0]["needs_review"] is False
    assert classification[0]["review_reason"] is None


def test_duplicate_flagged_files_appear_in_review_queue(tmp_path: Path):
    file_a = tmp_path / "report.pdf"
    file_b = tmp_path / "report_copy.pdf"
    file_a.write_bytes(b"pdf")
    file_b.write_bytes(b"pdf")

    ingestion_docs = [
        {
            "source_path": str(file_a),
            "file_name": file_a.name,
            "extraction_method": "native",
            "char_count": 10,
            "combined_text": "Environmental report",
        },
        {
            "source_path": str(file_b),
            "file_name": file_b.name,
            "extraction_method": "native",
            "char_count": 10,
            "combined_text": "Environmental report",
        },
    ]
    classification = [
        {
            "source_path": str(file_a),
            "category_id": "05",
            "category_folder": "05_Environmental",
            "confidence": "high",
            "score": 0.9,
            "method": "embedding",
            "reason": "matched",
            "supporting_terms": [],
            "entities": [],
            "needs_review": False,
            "review_reason": None,
            "api_used": False,
        },
        {
            "source_path": str(file_b),
            "category_id": "05",
            "category_folder": "05_Environmental",
            "confidence": "high",
            "score": 0.9,
            "method": "embedding",
            "reason": "matched",
            "supporting_terms": [],
            "entities": [],
            "needs_review": False,
            "review_reason": None,
            "api_used": False,
        },
    ]
    pairs = [_pair(file_a, file_b)]
    apply_duplicate_review_flags(classification, pairs)

    rows = build_manifest_rows(
        ingestion_docs,
        classification,
        tmp_path / "out",
        duplicate_pairs=pairs,
    )
    review_path = tmp_path / "review_queue.xlsx"
    write_review_queue(review_path, rows)

    review = read_review_queue(review_path)

    assert len(review) == 2
    for row in review:
        assert "Duplicate:" in row["review_reason"]
