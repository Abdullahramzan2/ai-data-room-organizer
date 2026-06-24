"""Format pipeline run summaries for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


def _artifact_line(name: str, path: str | None) -> tuple[str, str, bool] | None:
    if not path:
        return None
    file_path = Path(str(path))
    exists = file_path.is_file() or file_path.is_dir()
    mark = "✓" if exists else "—"
    return name, str(path), exists and mark == "✓"


def _render_summary_body(summary: dict[str, Any]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed", summary.get("processed", 0))
    c2.metric("Organized", summary.get("organized", 0))
    c3.metric("Review queue", summary.get("review_queue_count", 0))
    c4.metric("Duplicates", summary.get("duplicate_pair_count", 0))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("API calls", summary.get("api_used_count", 0))
    c6.metric("Skipped", summary.get("skipped_count", 0))
    c7.metric(
        "Failed",
        int(summary.get("ingestion_failed_count", 0)) + int(summary.get("organize_failed_count", 0)),
    )
    if summary.get("admin_mirrored_count") is not None:
        c8.metric("Admin mirrored", summary.get("admin_mirrored_count", 0))

    flags: list[str] = []
    if summary.get("rename"):
        flags.append("Rename on")
    if summary.get("ocr_enabled") is False:
        flags.append("OCR off")
    elif summary.get("ocr_enabled"):
        flags.append("OCR on")
    if summary.get("recursive") is False:
        flags.append("Non-recursive")
    if flags:
        st.caption(" · ".join(flags))

    if summary.get("rerun"):
        st.info(f"Rerun — {summary.get('corrections_applied', 0)} correction(s) applied.")

    timings = summary.get("timings") or {}
    if timings:
        st.markdown("**Timing (seconds)**")
        timing_labels = [
            ("Ingestion (OCR/extract)", "ingestion_seconds"),
            ("Classification", "classification_seconds"),
            ("Duplicates", "duplicates_seconds"),
            ("Organize", "organize_seconds"),
            ("Export", "export_seconds"),
            ("Total", "total_seconds"),
        ]
        cols = st.columns(3)
        shown = 0
        for label, key in timing_labels:
            if key in timings:
                cols[shown % 3].metric(label, timings[key])
                shown += 1

    st.markdown("**Paths**")
    for label, key in [("Input", "input_dir"), ("Output", "output_dir")]:
        value = summary.get(key, "")
        if value:
            st.text(f"{label}: {value}")

    admin_folder = summary.get("admin_folder")
    if admin_folder:
        st.text(f"Admin mirror: {admin_folder}")

    artifacts = [
        ("Manifest (CSV)", summary.get("manifest")),
        ("Manifest (Excel)", summary.get("manifest_xlsx")),
        ("Review queue", summary.get("review_queue")),
        ("HTML index", summary.get("index_html")),
        ("Duplicate report", summary.get("duplicate_report")),
        ("Errors report", summary.get("errors_report")),
        ("Classification log", summary.get("classification_log")),
        ("Processing log", summary.get("processing_log")),
        ("Audit log (API)", summary.get("audit_log")),
    ]
    existing: list[tuple[str, str, bool]] = []
    for name, path in artifacts:
        line = _artifact_line(name, str(path) if path else None)
        if line:
            existing.append(line)

    if existing:
        st.markdown("**Output files**")
        for name, path, ok in existing:
            mark = "✓" if ok else "—"
            st.markdown(f"- {mark} **{name}** — `{path}`")

    provider = summary.get("reasoning_provider")
    if provider:
        st.caption(f"Reasoning provider: {provider}")


def display_run_summary(
    summary: dict[str, Any],
    *,
    title: str = "Run summary",
    expanded: bool = False,
) -> None:
    """Render run summary inside a collapsible expander."""
    with st.expander(title, expanded=expanded):
        _render_summary_body(summary)
