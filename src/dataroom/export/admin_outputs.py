"""Admin artifact paths under taxonomy folder 00 (Carl data room layout)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Carl folder 00 deliverables — written under {output_dir}/{admin_folder}/.
ADMIN_ARTIFACT_KEYS = (
    "manifest",
    "review_queue",
    "duplicate_report",
    "errors_report",
    "index_html",
    "classification_log",
    "processing_log",
    "source_auth_matrix",
)


@dataclass(frozen=True)
class AdminArtifactPaths:
    admin_dir: Path
    manifest: Path
    review_queue: Path
    duplicate_report: Path
    errors_report: Path
    index_html: Path
    classification_log: Path
    processing_log: Path
    source_auth_matrix: Path

    def as_dict(self) -> dict[str, Path]:
        return {
            "manifest": self.manifest,
            "review_queue": self.review_queue,
            "duplicate_report": self.duplicate_report,
            "errors_report": self.errors_report,
            "index_html": self.index_html,
            "classification_log": self.classification_log,
            "processing_log": self.processing_log,
            "source_auth_matrix": self.source_auth_matrix,
        }


def admin_folder_name(config: dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) or {}
    return str(output_cfg.get("admin_folder", "00_Admin_and_Index"))


def keep_admin_artifacts_at_root(config: dict[str, Any]) -> bool:
    output_cfg = config.get("output", {}) or {}
    return bool(output_cfg.get("keep_admin_artifacts_at_root", False))


def resolve_admin_artifact_paths(output_dir: Path, config: dict[str, Any]) -> AdminArtifactPaths:
    """Primary paths for Carl admin deliverables inside folder 00."""
    output_cfg = config.get("output", {}) or {}
    admin_dir = output_dir / admin_folder_name(config)
    admin_dir.mkdir(parents=True, exist_ok=True)
    return AdminArtifactPaths(
        admin_dir=admin_dir,
        manifest=admin_dir / str(output_cfg.get("manifest_file", "manifest.xlsx")),
        review_queue=admin_dir / str(output_cfg.get("review_queue_file", "review_queue.xlsx")),
        duplicate_report=admin_dir / str(
            output_cfg.get("duplicate_report_file", "duplicate_report.xlsx")
        ),
        errors_report=admin_dir / str(output_cfg.get("errors_report_file", "errors_report.xlsx")),
        index_html=admin_dir / str(output_cfg.get("index_html_file", "index.html")),
        classification_log=admin_dir / str(
            output_cfg.get("classification_log_file", "classification_log.xlsx")
        ),
        processing_log=admin_dir / str(output_cfg.get("processing_log_file", "processing_log.json")),
        source_auth_matrix=admin_dir / str(
            output_cfg.get("source_auth_matrix_file", "source_authentication_matrix.xlsx")
        ),
    )


def resolve_artifact_path(
    output_dir: Path,
    config: dict[str, Any],
    *,
    summary_key: str | None,
    default_name: str,
    summary: dict[str, Any] | None = None,
) -> Path:
    """
    Locate an artifact for UI/CLI: summary path → admin folder 00 → legacy output root.

    ``run_summary.json`` always resolves to the output root (never folder 00).
    """
    if default_name == "run_summary.json":
        root_path = output_dir / "run_summary.json"
        if root_path.is_file():
            return root_path
        if summary_key and summary and summary.get(summary_key):
            path = Path(str(summary[summary_key]))
            if path.is_file():
                return path
        return root_path

    if summary_key and summary and summary.get(summary_key):
        path = Path(str(summary[summary_key]))
        if path.is_file():
            return path

    admin_path = output_dir / admin_folder_name(config) / default_name
    if admin_path.is_file():
        return admin_path

    return output_dir / default_name
