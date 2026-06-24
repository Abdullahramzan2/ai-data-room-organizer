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


class LiveProgressPanel:
    """In-place live progress using separate Streamlit placeholders (no stacking)."""

    def __init__(self) -> None:
        self._phase = st.empty()
        self._metrics = st.empty()
        self._progress = st.empty()
        self._files = st.empty()
        self._duplicates = st.empty()
        self._last_key: str | None = None

    def _snapshot_key(self, snapshot: dict[str, Any]) -> str:
        return "|".join(
            [
                str(snapshot.get("updated_at", "")),
                str(snapshot.get("status", "")),
                str(snapshot.get("phase", "")),
                str(snapshot.get("current_file", "")),
                str(snapshot.get("classified_count", "")),
                str(snapshot.get("review_queue_count", "")),
                str(len(snapshot.get("files") or [])),
                str(len(snapshot.get("duplicate_pairs") or [])),
            ]
        )

    def update(self, snapshot: dict[str, Any] | None, *, force: bool = False) -> None:
        if snapshot is None:
            self._phase = self._phase.empty()
            return

        status = str(snapshot.get("status", "running"))
        if not force and status not in {"complete", "failed"}:
            key = self._snapshot_key(snapshot)
            if key == self._last_key:
                return
            self._last_key = key

        total = int(snapshot.get("total_files", 0))
        classified = int(snapshot.get("classified_count", 0))
        review_count = int(snapshot.get("review_queue_count", 0))
        duplicates = int(snapshot.get("duplicate_pair_count", 0))
        failed = int(snapshot.get("failed_count", 0))

        self._phase = self._phase.empty()
        if status == "complete":
            self._phase.success("Pipeline finished.")
        elif status == "failed":
            self._phase.error(snapshot.get("error") or "Pipeline failed.")

        self._metrics = self._metrics.empty()
        self._progress = self._progress.empty()
        if status == "running":
            c1, c2, c3, c4, c5 = self._metrics.columns(5)
            c1.metric("Total files", total)
            c2.metric("Classified", classified)
            c3.metric("Review queue", review_count)
            c4.metric("Duplicates", duplicates)
            c5.metric("Failed", failed)
            if total > 0:
                self._progress.progress(
                    min(1.0, classified / total),
                    text=f"Classified {classified} of {total}",
                )

        self._files = self._files.empty()
        file_rows = _file_table_rows(snapshot)
        if file_rows:
            with self._files.container():
                st.markdown("**Files**")
                st.dataframe(
                    pd.DataFrame(file_rows),
                    hide_index=True,
                    width="stretch",
                    height=min(420, 38 + len(file_rows) * 35),
                )

        self._duplicates = self._duplicates.empty()
        dup_pairs = snapshot.get("duplicate_pairs") or []
        if dup_pairs:
            dup_rows = _duplicate_table_rows(dup_pairs)
            with self._duplicates.container():
                st.markdown("**Duplicate pairs**")
                st.dataframe(pd.DataFrame(dup_rows), hide_index=True, width="stretch")
