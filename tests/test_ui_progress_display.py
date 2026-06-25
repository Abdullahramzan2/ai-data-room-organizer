"""Tests for live progress display helpers."""

from __future__ import annotations

from dataroom.ui.progress_display import (
    LiveProgressPanel,
    _duplicate_table_rows,
    _file_table_rows,
    run_status_message,
)


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


def test_run_status_message_transitions():
    assert run_status_message(None, starting=True) == "Starting the pipeline…"
    assert run_status_message({"status": "running", "files": []}) == "Starting the pipeline…"
    assert run_status_message({"status": "running", "files": [{"file_name": "a.txt"}]}) == "Pipeline is running…"
    assert run_status_message({"status": "complete"}) == "Pipeline finished."


def test_repaint_run_status_uses_session_message():
    import streamlit as st

    st.session_state["_run_status_message"] = "Starting the pipeline…"
    st.session_state["_run_status_is_error"] = False
    from dataroom.ui.progress_display import repaint_run_status

    repaint_run_status()
    assert st.session_state["_run_status_message"] == "Starting the pipeline…"


def test_live_progress_panel_clear():
    panel = LiveProgressPanel()
    panel.clear()
    assert panel._last_metrics_key is None


def test_live_progress_panel_metrics_key_changes():
    panel = LiveProgressPanel()
    assert panel._metrics_key({"status": "running", "classified_count": 1}) != panel._metrics_key(
        {"status": "running", "classified_count": 2}
    )
