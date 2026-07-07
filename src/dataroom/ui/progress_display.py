"""Live pipeline progress display for Streamlit."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from dataroom.pipeline.progress import summarize_file_progress

_FRAGMENT_NO_DIM_CSS = """
<style>
div[data-testid="stFragment"] {
    opacity: 1 !important;
}
div[data-testid="stFragment"] * {
    opacity: 1 !important;
}
</style>
"""


def _status_icon(status: str) -> str:
    return {
        "pending": "⏳",
        "ingesting": "📥",
        "ingested": "📄",
        "classifying": "🤖",
        "done": "✅",
        "failed": "❌",
        "skipped": "⏭️",
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
        st.caption("Waiting for file list…")
        return
    st.markdown("**Files**")
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=min(420, 38 + len(rows) * 35),
    )


def _pipelined_overlap(snapshot: dict[str, Any], counts: dict[str, int]) -> bool:
    if str(snapshot.get("status", "")) != "running":
        return False
    phase = str(snapshot.get("phase", ""))
    return (
        counts.get("classifying", 0) > 0
        or counts.get("classified", 0) > 0
        or phase in {"classifying", "duplicates", "organizing", "exporting"}
    )


def render_live_run_dashboard(
    snapshot: dict[str, Any] | None,
    *,
    starting: bool = False,
) -> None:
    """Render metrics, progress bar, and file table for an active or finished run."""
    if snapshot is None:
        if starting:
            st.caption("Preparing pipeline…")
            st.markdown("**Files**")
            st.caption("Scanning input folder…")
        return

    status = str(snapshot.get("status", "running"))
    phase = str(snapshot.get("phase", ""))
    files = snapshot.get("files") or []
    counts = summarize_file_progress(files, total=int(snapshot.get("total_files", 0)))
    total = counts["total"]
    classified = counts["classified"]
    ingested = counts["ingested"]
    classifying = counts.get("classifying", 0)
    ingesting = counts.get("ingesting", 0)
    failed = counts["failed"]
    terminal = counts["terminal"]
    review_count = int(snapshot.get("review_queue_count", 0))
    duplicates = int(snapshot.get("duplicate_pair_count", 0))
    overlap = _pipelined_overlap(snapshot, counts)

    if total > 0 and status in {"running", "complete", "failed"}:
        if overlap and status == "running":
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            c1.metric("Total files", total)
            c2.metric("Ingesting", ingesting)
            c3.metric("Classifying", classifying)
            c4.metric("Classified", classified)
            c5.metric("Failed", failed)
            c6.metric("Review queue", review_count)
        else:
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Total files", total)
            if status == "running" and phase == "ingesting" and not overlap:
                c2.metric("Ingested", ingested)
            else:
                c2.metric("Classified", classified)
            c3.metric("Review queue", review_count)
            c4.metric("Duplicates", duplicates)
            c5.metric("Failed", failed)

    if total > 0 and status == "running":
        if overlap:
            done_steps = max(ingested, classified + classifying)
            st.progress(
                min(1.0, done_steps / total),
                text=(
                    f"Ingested {ingested}, classifying {classifying}, "
                    f"classified {classified} of {total}"
                ),
            )
        elif phase == "ingesting":
            st.progress(
                min(1.0, ingested / total),
                text=f"Ingested {ingested} of {total}",
            )
        elif phase == "classifying":
            st.progress(
                min(1.0, classified / total),
                text=f"Classified {classified} of {total}",
            )
        else:
            done_steps = max(ingested, classified)
            st.progress(
                min(1.0, done_steps / total),
                text=f"Processing… {done_steps} of {total}",
            )
    elif total > 0 and status in {"complete", "failed"}:
        if terminal >= total:
            if failed:
                label = f"Finished — {classified} classified, {failed} failed ({total} total)"
            else:
                label = f"Finished — {classified} of {total} classified"
            st.progress(1.0, text=label)
        else:
            st.progress(
                min(1.0, terminal / total),
                text=f"Finishing… {classified} classified, {ingested} ingested ({total} total)",
            )

    render_file_results_table(snapshot)

    dup_pairs = snapshot.get("duplicate_pairs") or []
    if dup_pairs:
        dup_rows = _duplicate_table_rows(dup_pairs)
        st.markdown("**Duplicate pairs**")
        st.dataframe(pd.DataFrame(dup_rows), hide_index=True, width="stretch")


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
    """Allocate a fresh status placeholder (Streamlit empties go stale after rerun)."""
    slot = st.empty()
    st.session_state["_run_status_slot"] = slot
    return slot


def run_status_message(snapshot: dict[str, Any] | None, *, starting: bool = False) -> str:
    if starting:
        return "Starting the pipeline…"
    if snapshot is None:
        return "Pipeline is running…"

    status = str(snapshot.get("status", ""))
    phase = str(snapshot.get("phase", ""))
    files = snapshot.get("files") or []
    counts = summarize_file_progress(files, total=int(snapshot.get("total_files", 0)))
    total = counts["total"]

    if status == "running":
        if phase == "scanning" or (total == 0 and not files):
            return "Scanning input folder…"
        if phase == "model_ready":
            return "Loading classification model…"
        if phase == "ingesting":
            return f"Ingesting files… {counts['ingested']} of {total}"
        if phase == "classifying":
            return f"Classifying files… {counts['classified']} of {total}"
        if phase == "duplicates":
            return "Detecting duplicates…"
        if phase == "organizing":
            return "Organizing files…"
        if phase == "exporting":
            return "Exporting results…"
        if total > 0 and counts["ingested"] < total:
            return f"Ingesting files… {counts['ingested']} of {total}"
        if total > 0 and counts["classified"] < total:
            return f"Classifying files… {counts['classified']} of {total}"
        return "Pipeline is running…"
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
    """Update the status line below the Run button (main page only, not inside fragments)."""
    message = _remember_run_status(snapshot, starting=starting, force=force)
    if not message:
        return
    _paint_run_status(message)


def _remember_run_status(
    snapshot: dict[str, Any] | None,
    *,
    starting: bool = False,
    force: bool = False,
) -> str:
    message = run_status_message(snapshot, starting=starting)
    if not message:
        return ""
    if not force and message == st.session_state.get("_run_status_message"):
        return message
    st.session_state["_run_status_message"] = message
    st.session_state["_run_status_is_error"] = (
        snapshot is not None and str(snapshot.get("status", "")) == "failed"
    )
    return message


def _paint_run_status(message: str) -> None:
    target = st.session_state.get("_run_status_slot")
    if target is None:
        return
    if message == "Pipeline finished.":
        target.success(message)
    elif st.session_state.get("_run_status_is_error"):
        target.error(message)
    else:
        target.info(message)


def _render_fragment_status(
    snapshot: dict[str, Any] | None,
    *,
    starting: bool = False,
    force: bool = False,
) -> None:
    """Render the live status alert inside the poll fragment (never uses outside placeholders)."""
    message = _remember_run_status(snapshot, starting=starting, force=force)
    if not message:
        return
    slot = st.empty()
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
                str(snapshot.get("phase", "")),
                str(snapshot.get("total_files", "")),
                str(snapshot.get("ingested_count", "")),
                str(snapshot.get("classified_count", "")),
                str(snapshot.get("review_queue_count", "")),
                str(snapshot.get("duplicate_pair_count", "")),
                str(snapshot.get("failed_count", "")),
            ]
        )

    def _progress_key(self, snapshot: dict[str, Any]) -> str:
        total = int(snapshot.get("total_files", 0))
        classified = int(snapshot.get("classified_count", 0))
        ingested = int(snapshot.get("ingested_count", 0))
        return (
            f"{snapshot.get('status', '')}:{snapshot.get('phase', '')}:"
            f"{ingested}/{classified}/{total}"
        )

    def _files_key(self, snapshot: dict[str, Any]) -> str:
        files = snapshot.get("files") or []
        return "|".join(
            f"{row.get('file_name')}:{row.get('status')}:{row.get('category_folder')}:"
            f"{row.get('confidence')}:{row.get('needs_review')}"
            for row in files
        )

    def _duplicates_key(self, snapshot: dict[str, Any]) -> str:
        pairs = snapshot.get("duplicate_pairs") or []
        return "|".join(
            f"{pair.get('file_a_path')}:{pair.get('file_b_path')}" for pair in pairs
        )

    def update(self, snapshot: dict[str, Any] | None, *, force: bool = False) -> None:
        if snapshot is None:
            return

        status = str(snapshot.get("status", "running"))
        phase = str(snapshot.get("phase", ""))
        files = snapshot.get("files") or []
        counts = summarize_file_progress(files, total=int(snapshot.get("total_files", 0)))
        total = counts["total"]
        classified = counts["classified"]
        ingested = counts["ingested"]
        classifying = counts.get("classifying", 0)
        ingesting = counts.get("ingesting", 0)
        failed = counts["failed"]
        terminal = counts["terminal"]
        review_count = int(snapshot.get("review_queue_count", 0))
        duplicates = int(snapshot.get("duplicate_pair_count", 0))
        overlap = _pipelined_overlap(snapshot, counts)

        metrics_key = "|".join(
            [
                status,
                phase,
                str(total),
                str(ingested),
                str(classifying),
                str(classified),
                str(review_count),
                str(duplicates),
                str(failed),
            ]
        )
        if force or metrics_key != self._last_metrics_key:
            self._last_metrics_key = metrics_key
            with self._metrics.container():
                if total > 0 and status in {"running", "complete", "failed"}:
                    if overlap and status == "running":
                        c1, c2, c3, c4, c5, c6 = st.columns(6)
                        c1.metric("Total files", total)
                        c2.metric("Ingesting", ingesting)
                        c3.metric("Classifying", classifying)
                        c4.metric("Classified", classified)
                        c5.metric("Failed", failed)
                        c6.metric("Review queue", review_count)
                    else:
                        c1, c2, c3, c4, c5 = st.columns(5)
                        c1.metric("Total files", total)
                        if status == "running" and phase == "ingesting" and not overlap:
                            c2.metric("Ingested", ingested)
                        else:
                            c2.metric("Classified", classified)
                        c3.metric("Review queue", review_count)
                        c4.metric("Duplicates", duplicates)
                        c5.metric("Failed", failed)

        progress_key = f"{status}:{phase}:{ingested}/{classifying}/{classified}/{terminal}/{total}"
        if force or progress_key != self._last_progress_key:
            self._last_progress_key = progress_key
            with self._progress.container():
                if total > 0 and status == "running":
                    if overlap:
                        done_steps = max(ingested, classified + classifying)
                        st.progress(
                            min(1.0, done_steps / total),
                            text=(
                                f"Ingested {ingested}, classifying {classifying}, "
                                f"classified {classified} of {total}"
                            ),
                        )
                    elif phase == "ingesting":
                        st.progress(
                            min(1.0, ingested / total),
                            text=f"Ingested {ingested} of {total}",
                        )
                    elif phase == "classifying":
                        st.progress(
                            min(1.0, classified / total),
                            text=f"Classified {classified} of {total}",
                        )
                    else:
                        done_steps = max(ingested, classified)
                        st.progress(
                            min(1.0, done_steps / total),
                            text=f"Processing… {done_steps} of {total}",
                        )
                elif total > 0 and status in {"complete", "failed"}:
                    if terminal >= total:
                        if failed:
                            label = (
                                f"Finished — {classified} classified, {failed} failed ({total} total)"
                            )
                        else:
                            label = f"Finished — {classified} of {total} classified"
                        st.progress(1.0, text=label)
                    else:
                        st.progress(
                            min(1.0, terminal / total),
                            text=f"Finishing… {classified} classified, {ingested} ingested ({total} total)",
                        )

        files_key = self._files_key(snapshot)
        refresh_files = force or files_key != self._last_files_key or status == "running"
        if refresh_files:
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
                    )
                elif status == "running":
                    st.markdown("**Files**")
                    st.caption("Scanning input folder…")

        duplicates_key = self._duplicates_key(snapshot)
        if force or duplicates_key != self._last_duplicates_key:
            self._last_duplicates_key = duplicates_key
            with self._duplicates.container():
                dup_pairs = snapshot.get("duplicate_pairs") or []
                if dup_pairs:
                    dup_rows = _duplicate_table_rows(dup_pairs)
                    st.markdown("**Duplicate pairs**")
                    st.dataframe(pd.DataFrame(dup_rows), hide_index=True, width="stretch")


def render_run_progress_poll_fragment(
    output_path: Path,
    config: dict[str, Any],
    *,
    on_complete: Callable[[], None] | None = None,
) -> None:
    """Poll run_progress.json while a background pipeline job is active."""
    from dataroom.ui.helpers import load_pipeline_progress
    from dataroom.ui.pipeline_runner import (
        PipelineSubprocessError,
        clear_active_pipeline_job,
        get_active_pipeline_job,
    )

    @st.fragment(run_every=timedelta(seconds=0.4))
    def _poll() -> None:
        if not st.session_state.get("pipeline_running"):
            return

        st.markdown(_FRAGMENT_NO_DIM_CSS, unsafe_allow_html=True)

        snapshot = load_pipeline_progress(output_path, config)
        if snapshot:
            st.session_state["_run_seen_progress"] = True
            _render_fragment_status(snapshot)
            render_live_run_dashboard(snapshot)
        elif not st.session_state.get("_run_seen_progress"):
            _render_fragment_status(None, starting=True)
            render_live_run_dashboard(None, starting=True)
        else:
            _render_fragment_status(None)
            render_live_run_dashboard(None, starting=True)

        job = get_active_pipeline_job()
        if job is None or not job.done:
            return

        final_progress = None
        try:
            if job.result is not None:
                st.session_state.pop("run_page_error", None)
                _render_fragment_status({"status": "complete"}, force=True)
                final_progress = load_pipeline_progress(output_path, config)
                if final_progress:
                    render_live_run_dashboard(final_progress)
            elif job.error is not None:
                if isinstance(job.error, PipelineSubprocessError):
                    st.session_state["run_page_error"] = str(job.error)
                else:
                    st.session_state["run_page_error"] = f"Pipeline failed: {job.error}"
                final_progress = load_pipeline_progress(output_path, config)
                if final_progress and str(final_progress.get("status", "")) == "failed":
                    _render_fragment_status(final_progress, force=True)
                    render_live_run_dashboard(final_progress)
                else:
                    _render_fragment_status(
                        {"status": "failed", "error": str(job.error)},
                        force=True,
                    )
            else:
                st.session_state.pop("run_page_error", None)
                final_progress = load_pipeline_progress(output_path, config)
                if final_progress:
                    _render_fragment_status(final_progress, force=True)
                    render_live_run_dashboard(final_progress)
        finally:
            clear_active_pipeline_job()
            st.session_state.pipeline_running = False
            st.session_state["_live_run_final_snapshot"] = final_progress if final_progress else None
            if on_complete is not None:
                on_complete()
            st.rerun()

    _poll()
