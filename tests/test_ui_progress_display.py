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
    assert run_status_message(None) == "Pipeline is running…"
    assert run_status_message({"status": "running", "phase": "classifying", "total_files": 3, "files": [
        {"status": "done", "category_folder": "01_Project_Overview"},
        {"status": "ingested"},
        {"status": "ingested"},
    ]}) == "Classifying files… 1 of 3"
    assert run_status_message({"status": "running", "phase": "ingesting", "total_files": 2, "files": [
        {"status": "ingested"},
        {"status": "ingesting"},
    ]}) == "Ingesting files… 1 of 2"
    assert run_status_message({"status": "complete"}) == "Pipeline finished."


def test_repaint_run_status_uses_session_message():
    import streamlit as st

    st.session_state["_run_status_message"] = "Starting the pipeline…"
    st.session_state["_run_status_is_error"] = False
    st.session_state["_run_status_slot"] = st.empty()
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


def test_live_progress_panel_progress_key_tracks_ingestion():
    panel = LiveProgressPanel()
    key_a = panel._progress_key(
        {"status": "running", "phase": "ingesting", "ingested_count": 1, "classified_count": 0, "total_files": 5}
    )
    key_b = panel._progress_key(
        {"status": "running", "phase": "ingesting", "ingested_count": 2, "classified_count": 0, "total_files": 5}
    )
    assert key_a != key_b


def test_summarize_file_progress_counts_classifying():
    from dataroom.pipeline.progress import summarize_file_progress

    files = [
        {"status": "ingesting"},
        {"status": "classifying"},
        {"status": "done", "category_folder": "01_Project_Overview"},
    ]
    counts = summarize_file_progress(files, total=3)
    assert counts["ingesting"] == 1
    assert counts["classifying"] == 1
    assert counts["classified"] == 1


def test_summarize_file_progress_counts_classified_only_with_folder():
    from dataroom.pipeline.progress import summarize_file_progress

    files = [
        {"status": "ingested"},
        {"status": "done", "category_folder": "01_Project_Overview"},
        {"status": "done"},
    ]
    counts = summarize_file_progress(files, total=3)
    assert counts["ingested"] == 3
    assert counts["classified"] == 1
    assert counts["terminal"] == 1
