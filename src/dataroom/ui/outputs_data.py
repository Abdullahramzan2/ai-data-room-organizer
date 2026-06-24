"""Outputs tab helpers — manifest preview, logs, admin mirror (no Streamlit)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from dataroom.config import load_app_config
from dataroom.export.admin_outputs import resolve_artifact_path
from dataroom.ui.helpers import load_run_summary

MANIFEST_PREVIEW_COLUMNS = [
    "file_name",
    "category_folder",
    "confidence",
    "duplicate_status",
    "document_type",
    "needs_review",
    "text_snippet",
    "output_path",
]


def manifest_csv_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    summary = load_run_summary(output_dir)
    return resolve_artifact_path(
        output_dir,
        config,
        summary_key="manifest",
        default_name=str(output_cfg.get("manifest_file", "manifest.csv")),
        summary=summary,
    )


def load_manifest_rows(
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
    limit: int | None = None,
) -> list[dict[str, str]]:
    path = manifest_csv_path(output_dir, config)
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if limit is not None:
        return rows[:limit]
    return rows


def load_manifest_preview_rows(
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
    limit: int = 200,
) -> list[dict[str, str]]:
    """Manifest rows with Carl acceptance columns for UI preview."""
    preview: list[dict[str, str]] = []
    for row in load_manifest_rows(output_dir, config=config, limit=limit):
        preview.append({col: row.get(col, "") for col in MANIFEST_PREVIEW_COLUMNS})
    return preview


def load_processing_log(
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    summary = load_run_summary(output_dir)
    if summary and summary.get("processing_log"):
        path = Path(str(summary["processing_log"]))
    else:
        path = output_dir / str(output_cfg.get("processing_log_file", "processing_log.json"))
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def audit_log_path(output_dir: Path, *, config: dict[str, Any] | None = None) -> Path:
    summary = load_run_summary(output_dir)
    if summary and summary.get("audit_log"):
        return Path(str(summary["audit_log"]))
    return output_dir / "audit_log.jsonl"


def list_admin_mirror_files(admin_dir: Path) -> list[dict[str, str]]:
    if not admin_dir.is_dir():
        return []
    rows: list[dict[str, str]] = []
    for path in sorted(admin_dir.iterdir()):
        if path.is_file():
            rows.append({"file": path.name, "path": str(path)})
    return rows


def count_review_reason_matches(rows: list[dict[str, str]], needle: str) -> int:
    needle_lower = needle.lower()
    return sum(1 for row in rows if needle_lower in str(row.get("review_reason", "")).lower())
