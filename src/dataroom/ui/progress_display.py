"""Live pipeline progress display for Streamlit."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


def _status_icon(status: str) -> str:
    return {
        "pending": "⏳",
        "ingesting": "📥",
        "ingested": "📄",
        "classifying": "🤖",
        "done": "✅",
        "failed": "❌",
    }.get(status, "•")


def _file_table_rows(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    files = snapshot.get("files") or []
    return [
        {
            "": _status_icon(str(row.get("status", ""))),
            "File": str(row.get("file_name", "")),
            "Status": str(row.get("status", "")),
            "Folder": str(row.get("category_folder", "") or "—"),
            "Confidence": str(row.get("confidence", "") or "—"),
            "Review": "yes" if row.get("needs_review") else "",
        }
        for row in files
    ]


def _duplicate_table_rows(pairs: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for pair in pairs:
        file_a = Path(str(pair.get("file_a_path", ""))).name
        file_b = Path(str(pair.get("file_b_path", ""))).name
        rows.append(
            {
                "Type": str(pair.get("duplicate_type", "")),
                "File A": file_a,
                "File B": file_b,
                "Similarity": str(pair.get("similarity_score", "")),
                "Action": str(pair.get("recommended_action", "")),
            }
        )
    return rows


def render_file_results_table(snapshot: dict[str, Any]) -> None:
    """Render the per-file results table (shared by Run and Outputs)."""
    rows = _file_table_rows(snapshot)
    if not rows:
        st.caption("No files yet.")
        return
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=min(420, 38 + len(rows) * 35),
    )


def render_duplicate_pairs_table(pairs: list[dict[str, Any]]) -> None:
    """Render linked duplicate pairs."""
    rows = _duplicate_table_rows(pairs)
    if not rows:
        st.caption("No duplicate pairs detected.")
        return
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=min(320, 38 + len(rows) * 35),
    )


def get_run_status_slot() -> Any:
    slot = st.session_state.get("_run_status_slot")
    if slot is None:
        slot = st.empty()
        st.session_state["_run_status_slot"] = slot
    return slot


def run_status_message(snapshot: dict[str, Any] | None, *, starting: bool = False) -> str:
    if starting:
        return "Starting the pipeline…"
    if snapshot is None:
        return ""

    status = str(snapshot.get("status", ""))
    files = snapshot.get("files") or []
    if status == "running":
        return "Pipeline is running…" if files else "Starting the pipeline…"
    if status == "complete":
        return "Pipeline finished."
    if status == "failed":
        return str(snapshot.get("error") or "Pipeline failed.")
    return ""


def update_run_status(
    snapshot: dict[str, Any] | None,
    *,
    starting: bool = False,
    force: bool = False,
) -> None:
    """Update the single status line below the Run button."""
    message = run_status_message(snapshot, starting=starting)
    if not message:
        return
    if not force and message == st.session_state.get("_run_status_message"):
        return

    st.session_state["_run_status_message"] = message
    st.session_state["_run_status_is_error"] = (
        snapshot is not None and str(snapshot.get("status", "")) == "failed"
    )
    _paint_run_status(message)


def _paint_run_status(message: str) -> None:
    slot = get_run_status_slot()
    if message == "Pipeline finished.":
        slot.success(message)
    elif st.session_state.get("_run_status_is_error"):
        slot.error(message)
    else:
        slot.info(message)


def repaint_run_status() -> None:
    """Re-draw status after st.rerun (placeholders do not keep their content)."""
    message = st.session_state.get("_run_status_message", "")
    if message:
        _paint_run_status(message)


def _panel_session_key(output_path: Path) -> str:
    return f"_live_progress_panel_{output_path.resolve()}"


def reset_live_progress_panel(output_path: Path) -> None:
    st.session_state.pop(_panel_session_key(output_path), None)
    st.session_state.pop("_run_status_slot", None)
    st.session_state.pop("_run_status_message", None)
    st.session_state.pop("_run_status_is_error", None)


def get_live_progress_panel(output_path: Path) -> LiveProgressPanel:
    key = _panel_session_key(output_path)
    resolved = str(output_path.resolve())
    tracked = st.session_state.get("_live_panel_output")
    if tracked != resolved:
        if tracked:
            st.session_state.pop(_panel_session_key(Path(tracked)), None)
        st.session_state["_live_panel_output"] = resolved
        st.session_state.pop(key, None)

    panel = st.session_state.get(key)
    if panel is None:
        panel = LiveProgressPanel()
        st.session_state[key] = panel
    return panel


class LiveProgressPanel:
    """Live metrics and result tables below the Run button status line."""

    def __init__(self) -> None:
        self._metrics = st.empty()
        self._progress = st.empty()
        self._files = st.empty()
        self._duplicates = st.empty()
        self._last_metrics_key: str | None = None
        self._last_progress_key: str | None = None
        self._last_files_key: str | None = None
        self._last_duplicates_key: str | None = None

    def clear(self) -> None:
        self._last_metrics_key = None
        self._last_progress_key = None
        self._last_files_key = None
        self._last_duplicates_key = None
        self._metrics.empty()
        self._progress.empty()
        self._files.empty()
        self._duplicates.empty()

    def _metrics_key(self, snapshot: dict[str, Any]) -> str:
        return "|".join(
            [
                str(snapshot.get("status", "")),
                str(snapshot.get("total_files", "")),
                str(snapshot.get("classified_count", "")),
                str(snapshot.get("review_queue_count", "")),
                str(snapshot.get("duplicate_pair_count", "")),
                str(snapshot.get("failed_count", "")),
            ]
        )

    def _progress_key(self, snapshot: dict[str, Any]) -> str:
        total = int(snapshot.get("total_files", 0))
        classified = int(snapshot.get("classified_count", 0))
        return f"{snapshot.get('status', '')}:{classified}/{total}"

    def _files_key(self, snapshot: dict[str, Any]) -> str:
        files = snapshot.get("files") or []
        return "|".join(
            f"{row.get('file_name')}:{row.get('status')}:{row.get('category_folder')}:{row.get('confidence')}"
            for row in files
        )

    def _duplicates_key(self, snapshot: dict[str, Any]) -> str:
        pairs = snapshot.get("duplicate_pairs") or []
        return "|".join(
            f"{pair.get('file_a_path')}:{pair.get('file_b_path')}" for pair in pairs
        )

    def update(self, snapshot: dict[str, Any] | None, *, force: bool = False) -> None:
        if snapshot is None:
            self.clear()
            return

        status = str(snapshot.get("status", "running"))
        total = int(snapshot.get("total_files", 0))
        classified = int(snapshot.get("classified_count", 0))
        review_count = int(snapshot.get("review_queue_count", 0))
        duplicates = int(snapshot.get("duplicate_pair_count", 0))
        failed = int(snapshot.get("failed_count", 0))

        metrics_key = self._metrics_key(snapshot)
        if force or metrics_key != self._last_metrics_key:
            self._last_metrics_key = metrics_key
            with self._metrics.container():
                if status == "running":
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Total files", total)
                    c2.metric("Classified", classified)
                    c3.metric("Review queue", review_count)
                    c4.metric("Duplicates", duplicates)
                    c5.metric("Failed", failed)

        progress_key = self._progress_key(snapshot)
        if force or progress_key != self._last_progress_key:
            self._last_progress_key = progress_key
            with self._progress.container():
                if status == "running" and total > 0:
                    st.progress(
                        min(1.0, classified / total),
                        text=f"Classified {classified} of {total}",
                    )

        files_key = self._files_key(snapshot)
        if force or files_key != self._last_files_key:
            self._last_files_key = files_key
            with self._files.container():
                file_rows = _file_table_rows(snapshot)
                if file_rows:
                    st.markdown("**Files**")
                    st.dataframe(
                        pd.DataFrame(file_rows),
                        hide_index=True,
                        width="stretch",
                        height=min(420, 38 + len(file_rows) * 35),
                        key="pipeline_live_files",
                    )

        duplicates_key = self._duplicates_key(snapshot)
        if force or duplicates_key != self._last_duplicates_key:
            self._last_duplicates_key = duplicates_key
            with self._duplicates.container():
                dup_pairs = snapshot.get("duplicate_pairs") or []
                if dup_pairs:
                    dup_rows = _duplicate_table_rows(dup_pairs)
                    st.markdown("**Duplicate pairs**")
                    st.dataframe(pd.DataFrame(dup_rows), hide_index=True, width="stretch")
