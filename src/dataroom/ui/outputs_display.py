"""Outputs tab display — manifest preview, logs, admin mirror."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from dataroom.ui.outputs_data import (
    audit_log_path,
    list_admin_mirror_files,
    load_manifest_preview_rows,
    load_processing_log,
)


def display_processing_log_panel(
    output_dir: Path,
    *,
    config: dict[str, Any],
    summary: dict[str, Any] | None = None,
) -> None:
    payload = load_processing_log(output_dir, config=config)
    if payload is None:
        return

    st.subheader("Processing log")
    counts = payload.get("counts") or {}
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Processed", counts.get("processed", 0))
    c2.metric("Review queue", counts.get("review_queue", 0))
    c3.metric("Duplicate pairs", counts.get("duplicate_pairs", 0))
    c4.metric("API used", counts.get("api_used", 0))

    meta_cols = st.columns(4)
    meta_cols[0].caption(f"Started: {payload.get('started_at', '—')}")
    meta_cols[1].caption(f"Finished: {payload.get('finished_at', '—')}")
    meta_cols[2].caption(f"OCR: {'yes' if payload.get('ocr_enabled') else 'no'}")
    meta_cols[3].caption(f"Rename: {'yes' if payload.get('rename') else 'no'}")

    taxonomy = f"{payload.get('taxonomy_name', '')} v{payload.get('taxonomy_version', '')}".strip()
    if taxonomy and taxonomy != "v":
        st.caption(f"Taxonomy: {taxonomy}")

    log_path = (summary or {}).get("processing_log") or str(
        output_dir / config.get("output", {}).get("processing_log_file", "processing_log.json")
    )
    st.caption(f"Full log: `{log_path}`")


def display_manifest_preview(
    output_dir: Path,
    *,
    config: dict[str, Any],
    limit: int = 200,
) -> None:
    rows = load_manifest_preview_rows(output_dir, config=config, limit=limit)
    if not rows:
        return

    st.subheader("Manifest preview")
    st.caption(
        "Key acceptance columns — open `manifest.csv` / `manifest.xlsx` or `index.html` for the full index."
    )
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=min(480, 38 + len(rows) * 35),
        column_config={
            "text_snippet": st.column_config.TextColumn(width="large"),
            "output_path": st.column_config.TextColumn(width="medium"),
        },
    )


def display_admin_mirror_panel(summary: dict[str, Any]) -> None:
    admin_folder = summary.get("admin_folder")
    if not admin_folder:
        return

    admin_dir = Path(str(admin_folder))
    files = list_admin_mirror_files(admin_dir)
    if not files:
        return

    st.subheader("Admin folder mirror")
    st.caption(
        f"Carl folder 00 deliverables in `{admin_dir.name}/` — master index, manifest, logs, review queue, duplicate report, source auth matrix."
    )
    mirrored = int(summary.get("admin_artifact_count") or summary.get("admin_mirrored_count") or len(files))
    st.metric("Admin files in folder 00", mirrored)
    st.dataframe(
        pd.DataFrame(files),
        hide_index=True,
        width="stretch",
        height=min(320, 38 + len(files) * 35),
    )


def display_audit_log_hint(output_dir: Path, *, config: dict[str, Any]) -> None:
    path = audit_log_path(output_dir, config=config)
    if not path.is_file():
        return
    st.caption(f"Tier 3 API audit trail: `{path}` (guardrails only — separate from classification_log.csv)")
