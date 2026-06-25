"""Shared helpers for the Streamlit UI (no Streamlit import)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataroom.config import load_app_config, resolve_project_root
from dataroom.duplicates.report import DUPLICATE_REPORT_COLUMNS
from dataroom.export.admin_outputs import admin_folder_name, resolve_artifact_path
from dataroom.export.xlsx_io import read_table_xlsx
from dataroom.pipeline.progress import default_progress_path, load_run_progress


def default_config_path() -> Path:
    return resolve_project_root() / "config" / "default.yaml"


def load_run_summary(output_dir: Path) -> dict[str, Any] | None:
    summary_path = output_dir / "run_summary.json"
    if not summary_path.is_file():
        return None
    return json.loads(summary_path.read_text(encoding="utf-8"))


def progress_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    config = config or load_app_config()
    return default_progress_path(output_dir, config)


def load_pipeline_progress(output_dir: Path, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return load_run_progress(progress_path(output_dir, config))


def load_duplicate_report_rows(output_dir: Path, config: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Read duplicate_report.xlsx if present."""
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    summary = load_run_summary(output_dir)
    report_path = resolve_artifact_path(
        output_dir,
        config,
        summary_key="duplicate_report",
        default_name=str(output_cfg.get("duplicate_report_file", "duplicate_report.xlsx")),
        summary=summary,
    )
    return read_table_xlsx(report_path, DUPLICATE_REPORT_COLUMNS)


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
        ("manifest.xlsx", "manifest", output_cfg.get("manifest_file", "manifest.xlsx")),
        ("review_queue.xlsx", "review_queue", output_cfg.get("review_queue_file", "review_queue.xlsx")),
        (
            "duplicate_report.xlsx",
            "duplicate_report",
            output_cfg.get("duplicate_report_file", "duplicate_report.xlsx"),
        ),
        ("index.html", "index_html", output_cfg.get("index_html_file", "index.html")),
        ("errors_report.xlsx", "errors_report", output_cfg.get("errors_report_file", "errors_report.xlsx")),
        (
            "source_authentication_matrix.xlsx",
            "source_auth_matrix",
            output_cfg.get("source_auth_matrix_file", "source_authentication_matrix.xlsx"),
        ),
        (
            "classification_log.xlsx",
            "classification_log",
            output_cfg.get("classification_log_file", "classification_log.xlsx"),
        ),
        (
            "processing_log.json",
            "processing_log",
            output_cfg.get("processing_log_file", "processing_log.json"),
        ),
        ("audit_log.jsonl", "audit_log", "audit_log.jsonl"),
        ("run_summary.json", None, "run_summary.json"),
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
        ("run_progress.json", None, output_cfg.get("progress_file", "run_progress.json")),
    ]

    artifacts: list[dict[str, str]] = []
    admin_folder = admin_folder_name(config)
    for label, summary_key, default_name in artifact_defs:
        if summary_key in {
            "manifest",
            "review_queue",
            "duplicate_report",
            "index_html",
            "errors_report",
            "classification_log",
            "source_auth_matrix",
        }:
            path = resolve_artifact_path(
                output_dir,
                config,
                summary_key=summary_key,
                default_name=str(default_name),
                summary=summary,
            )
        elif summary and summary_key and summary.get(summary_key):
            path = Path(str(summary[summary_key]))
        elif label in {"processing_log.json", "run_summary.json", "run_progress.json"}:
            path = resolve_artifact_path(
                output_dir,
                config,
                summary_key=summary_key,
                default_name=str(default_name),
                summary=summary,
            )
        elif label == "audit_log.jsonl":
            path = output_dir / "audit_log.jsonl"
        else:
            path = output_dir / str(default_name)
        location = admin_folder if admin_folder in str(path) else "output root"
        artifacts.append(
            {
                "artifact": label,
                "path": str(path),
                "location": location,
                "exists": "yes" if path.is_file() else "no",
            }
        )

    if summary and summary.get("admin_folder"):
        admin_dir = Path(str(summary["admin_folder"]))
        artifacts.append(
            {
                "artifact": f"{admin_folder}/",
                "path": str(admin_dir),
                "location": admin_folder,
                "exists": "yes" if admin_dir.is_dir() else "no",
            }
        )
    return artifacts


def review_queue_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    config = config or load_app_config()
    output_cfg = config.get("output", {}) or {}
    summary = load_run_summary(output_dir)
    return resolve_artifact_path(
        output_dir,
        config,
        summary_key="review_queue",
        default_name=str(output_cfg.get("review_queue_file", "review_queue.xlsx")),
        summary=summary,
    )
