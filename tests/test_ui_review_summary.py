"""Tests for review queue summary lines in the UI."""

from __future__ import annotations

from dataroom.ui.app import _review_queue_summary_lines


def test_review_summary_all_flag_types():
    rows = [
        {"review_reason": "Duplicate: exact duplicate of file_b.pdf"},
        {"review_reason": "Low confidence (0.42): weak embedding match"},
        {"review_reason": "Medium confidence (0.55): keyword overlap"},
        {"review_reason": "Uncertain classification"},
    ]
    lines = _review_queue_summary_lines(rows)
    text = "\n".join(lines)
    assert "4 file(s) in the review queue." in text
    assert "1 flagged for duplicate review." in text
    assert "1 flagged for low confidence." in text
    assert "1 flagged for medium confidence." in text
    assert "1 flagged for other review reasons." in text


def test_review_summary_duplicate_only():
    rows = [
        {"review_reason": "Duplicate: near duplicate"},
        {"review_reason": "Low confidence | Duplicate: exact duplicate"},
    ]
    lines = _review_queue_summary_lines(rows)
    text = "\n".join(lines)
    assert "2 file(s) in the review queue." in text
    assert "2 flagged for duplicate review." in text
    assert "low confidence" not in text
