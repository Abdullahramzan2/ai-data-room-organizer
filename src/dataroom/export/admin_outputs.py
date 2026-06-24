"""Copy admin artifacts into the organized 00_Admin_and_Index folder."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

# Keys in artifact_paths dict passed from export_pipeline_outputs / finalize.
ADMIN_MIRROR_KEYS = (
    "manifest",
    "manifest_xlsx",
    "review_queue",
    "duplicate_report",
    "errors_report",
    "index_html",
    "run_summary",
    "classification_log",
    "processing_log",
)


def admin_folder_name(config: dict[str, Any]) -> str:
    output_cfg = config.get("output", {}) or {}
    return str(output_cfg.get("admin_folder", "00_Admin_and_Index"))


def should_mirror_admin_artifacts(config: dict[str, Any]) -> bool:
    output_cfg = config.get("output", {}) or {}
    return bool(output_cfg.get("mirror_admin_artifacts", True))


def mirror_admin_artifacts(
    output_dir: Path,
    config: dict[str, Any],
    artifact_paths: dict[str, Path],
) -> list[Path]:
    """
    Copy admin artifacts into {output_dir}/{admin_folder}/.

    Root copies are preserved for CLI/UI paths. Returns paths of mirrored files.
    """
    if not should_mirror_admin_artifacts(config):
        return []

    admin_dir = output_dir / admin_folder_name(config)
    admin_dir.mkdir(parents=True, exist_ok=True)
    mirrored: list[Path] = []

    for key in ADMIN_MIRROR_KEYS:
        source = artifact_paths.get(key)
        if source is None or not source.is_file():
            continue
        dest = admin_dir / source.name
        shutil.copy2(source, dest)
        mirrored.append(dest)

    return mirrored
