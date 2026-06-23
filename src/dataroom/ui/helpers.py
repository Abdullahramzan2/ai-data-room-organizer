"""Shared helpers for the Streamlit UI (no Streamlit import)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataroom.config import load_app_config, resolve_project_root


def default_config_path() -> Path:
    return resolve_project_root() / "config" / "default.yaml"


def load_run_summary(output_dir: Path) -> dict[str, Any] | None:
    summary_path = output_dir / "run_summary.json"
    if not summary_path.is_file():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def taxonomy_folder_names(taxonomy: dict[str, Any]) -> list[str]:
    folders: list[str] = []
    for cat in taxonomy.get("categories", []):
        folder = str(cat.get("folder", "")).strip()
        if folder:
            folders.append(folder)
    return folders


def list_output_artifacts(
    output_dir: Path,
    *,
    config: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Return key output files with existence status."""
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    summary = load_run_summary(output_dir)

    artifact_defs = [
        ("manifest.csv", "manifest", output_cfg.get("manifest_file", "manifest.csv")),
        ("manifest.xlsx", "manifest_xlsx", output_cfg.get("manifest_xlsx_file", "manifest.xlsx")),
        ("review_queue.csv", "review_queue", output_cfg.get("review_queue_file", "review_queue.csv")),
        (
            "duplicate_report.csv",
            "duplicate_report",
            output_cfg.get("duplicate_report_file", "duplicate_report.csv"),
        ),
        ("index.html", "index_html", output_cfg.get("index_html_file", "index.html")),
        ("errors_report.csv", "errors_report", output_cfg.get("errors_report_file", "errors_report.csv")),
        (
            "ingestion_cache.json",
            "ingestion_cache",
            output_cfg.get("ingestion_cache_file", "ingestion_cache.json"),
        ),
        (
            "classification_cache.json",
            "classification_cache",
            output_cfg.get("classification_cache_file", "classification_cache.json"),
        ),
        ("run_summary.json", None, "run_summary.json"),
    ]

    artifacts: list[dict[str, str]] = []
    for label, summary_key, default_name in artifact_defs:
        if summary and summary_key and summary.get(summary_key):
            path = Path(str(summary[summary_key]))
        else:
            path = output_dir / str(default_name)
        artifacts.append(
            {
                "artifact": label,
                "path": str(path),
                "exists": "yes" if path.is_file() else "no",
            }
        )
    return artifacts


def review_queue_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    return output_dir / output_cfg.get("review_queue_file", "review_queue.csv")
