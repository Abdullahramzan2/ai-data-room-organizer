"""Format pipeline run summaries for the Streamlit UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st


def display_run_summary(summary: dict[str, Any], *, title: str = "Run summary") -> None:
    """Render a readable run summary instead of raw JSON."""
    st.subheader(title)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed", summary.get("processed", 0))
    c2.metric("Organized", summary.get("organized", 0))
    c3.metric("Review queue", summary.get("review_queue_count", 0))
    c4.metric("Duplicates", summary.get("duplicate_pair_count", 0))

    c5, c6, c7 = st.columns(3)
    c5.metric("API calls", summary.get("api_used_count", 0))
    c6.metric("Skipped", summary.get("skipped_count", 0))
    c7.metric("Failed", int(summary.get("ingestion_failed_count", 0)) + int(summary.get("organize_failed_count", 0)))

    if summary.get("rerun"):
        st.info(f"Rerun — {summary.get('corrections_applied', 0)} correction(s) applied.")

    st.markdown("**Paths**")
    path_rows = [
        ("Input", summary.get("input_dir", "")),
        ("Output", summary.get("output_dir", "")),
    ]
    for label, value in path_rows:
        if value:
            st.text(f"{label}: {value}")

    artifacts = [
        ("Manifest (CSV)", summary.get("manifest")),
        ("Manifest (Excel)", summary.get("manifest_xlsx")),
        ("Review queue", summary.get("review_queue")),
        ("HTML index", summary.get("index_html")),
        ("Duplicate report", summary.get("duplicate_report")),
        ("Errors report", summary.get("errors_report")),
    ]
    existing = [(name, path) for name, path in artifacts if path]
    if existing:
        st.markdown("**Output files**")
        for name, path in existing:
            file_path = Path(str(path))
            exists = "✓" if file_path.is_file() else "—"
            st.markdown(f"- {exists} **{name}** — `{path}`")

    provider = summary.get("reasoning_provider")
    if provider:
        st.caption(f"Reasoning provider: {provider}")

    with st.expander("Technical details (JSON)"):
        st.json(summary)
