"""Tests for live progress display helpers."""

from __future__ import annotations

from dataroom.ui.progress_display import LiveProgressPanel, _duplicate_table_rows, _file_table_rows


def test_file_table_rows():
    snapshot = {
        "files": [
            {
                "file_name": "a.pdf",
                "status": "done",
                "category_folder": "01_Project_Overview",
                "confidence": "high",
                "needs_review": False,
            }
        ]
    }
    rows = _file_table_rows(snapshot)
    assert rows[0]["File"] == "a.pdf"
    assert rows[0]["Status"] == "done"


def test_duplicate_table_rows_uses_basenames():
    rows = _duplicate_table_rows(
        [
            {
                "duplicate_type": "exact",
                "file_a_path": r"C:\in\a.pdf",
                "file_b_path": r"C:\in\b.pdf",
                "similarity_score": "1.0",
                "recommended_action": "likely_duplicate",
            }
        ]
    )
    assert rows[0]["File A"] == "a.pdf"
    assert rows[0]["File B"] == "b.pdf"


def test_live_progress_panel_snapshot_key_changes():
    panel = LiveProgressPanel()
    assert panel._snapshot_key({"updated_at": "a", "status": "running", "files": []}) != panel._snapshot_key(
        {"updated_at": "b", "status": "running", "files": []}
    )
