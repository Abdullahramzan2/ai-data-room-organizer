"""Write and finalize pipeline output artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataroom.duplicates.models import DuplicatePair
from dataroom.export import (
    build_ingestion_error_rows,
    build_manifest_rows,
    build_organize_error_rows,
    write_errors_report,
    write_html_index,
    write_manifest_xlsx,
    write_review_queue,
)
from dataroom.export.admin_outputs import (
    keep_admin_artifacts_at_root,
    resolve_admin_artifact_paths,
)
from dataroom.export.classification_log import (
    build_classification_log_rows,
    build_processing_log,
    utc_now_iso,
    write_classification_log,
    write_processing_log,
)
from dataroom.duplicates import write_duplicate_report
from dataroom.export.source_auth_matrix import write_source_authentication_matrix
from dataroom.organizer.models import OrganizeResult
from dataroom.pipeline.cache import (
    build_classification_cache_payload,
    write_classification_cache,
)


def _maybe_copy_to_root(admin_path: Path, output_dir: Path, config: dict[str, Any]) -> None:
    """Optional legacy copy at output root when keep_admin_artifacts_at_root is enabled."""
    if not keep_admin_artifacts_at_root(config):
        return
    if not admin_path.is_file():
        return
    import shutil

    dest = output_dir / admin_path.name
    shutil.copy2(admin_path, dest)


def export_pipeline_outputs(
    *,
    output_dir: Path,
    config: dict[str, Any],
    ingestion_docs: list[dict[str, Any]],
    classification_results: list[dict[str, Any]],
    organized: list[OrganizeResult],
    duplicate_pairs: list[DuplicatePair],
    skipped_files: list[Path],
    failed_files: list[tuple[Path, str]],
    rename: bool,
    input_dir: Path | None = None,
    persist_classification_cache: bool = True,
    extra_summary: dict[str, Any] | None = None,
    run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write manifests, review queue, caches, and run_summary.json."""
    output_cfg = config.get("output", {})
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = build_manifest_rows(
        ingestion_docs,
        classification_results,
        output_dir,
        rename=rename,
        organize_results=organized,
        duplicate_pairs=duplicate_pairs,
    )
    admin_paths = resolve_admin_artifact_paths(output_dir, config)
    manifest_path = admin_paths.manifest
    review_path = admin_paths.review_queue
    errors_path = admin_paths.errors_report
    duplicate_path = admin_paths.duplicate_report
    index_html_path = admin_paths.index_html
    classification_log_path = admin_paths.classification_log
    source_auth_path = admin_paths.source_auth_matrix
    classification_cache_path = output_dir / output_cfg.get(
        "classification_cache_file", "classification_cache.json"
    )

    write_manifest_xlsx(manifest_path, manifest_rows)
    write_review_queue(review_path, manifest_rows, failed_files=failed_files)
    write_duplicate_report(duplicate_path, duplicate_pairs)
    write_html_index(
        index_html_path,
        manifest_rows,
        link_mode=str(output_cfg.get("index_link_mode", "original")),
        output_dir=output_dir,
    )
    write_source_authentication_matrix(source_auth_path, manifest_rows)

    error_rows = build_ingestion_error_rows(skipped_files, failed_files)
    error_rows.extend(build_organize_error_rows(organized))
    write_errors_report(errors_path, error_rows)

    log_timestamp = str((run_context or {}).get("started_at") or utc_now_iso())
    classification_log_rows = build_classification_log_rows(
        manifest_rows,
        timestamp=log_timestamp,
    )
    write_classification_log(classification_log_path, classification_log_rows)

    for admin_file in (
        manifest_path,
        review_path,
        duplicate_path,
        errors_path,
        index_html_path,
        classification_log_path,
        source_auth_path,
    ):
        _maybe_copy_to_root(admin_file, output_dir, config)

    if persist_classification_cache:
        write_classification_cache(
            classification_cache_path,
            build_classification_cache_payload(classification_results),
        )

    api_used_count = sum(1 for r in classification_results if r.get("api_used"))
    review_count = sum(1 for r in manifest_rows if r.get("needs_review") == "true") + len(
        failed_files
    )
    organized_success = sum(1 for r in organized if r.success)
    ingestion_cache_path = output_dir / output_cfg.get(
        "ingestion_cache_file", "ingestion_cache.json"
    )
    persist_cache = output_cfg.get("persist_ingestion_cache", True)

    summary: dict[str, Any] = {
        "input_dir": str(input_dir) if input_dir is not None else "",
        "output_dir": str(output_dir),
        "processed": len(ingestion_docs),
        "organized": organized_success,
        "skipped_count": len(skipped_files),
        "ingestion_failed_count": len(failed_files),
        "organize_failed_count": sum(1 for r in organized if not r.success),
        "review_queue_count": review_count,
        "api_used_count": api_used_count,
        "manifest": str(manifest_path),
        "review_queue": str(review_path),
        "errors_report": str(errors_path),
        "duplicate_report": str(duplicate_path),
        "duplicate_pair_count": len(duplicate_pairs),
        "index_html": str(index_html_path),
        "classification_log": str(classification_log_path),
        "source_auth_matrix": str(source_auth_path),
        "index_link_mode": str(output_cfg.get("index_link_mode", "original")),
        "ingestion_cache": str(ingestion_cache_path) if persist_cache else "",
        "classification_cache": str(classification_cache_path) if persist_classification_cache else "",
        "persist_ingestion_cache": persist_cache,
    }
    if extra_summary:
        summary.update(extra_summary)

    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def finalize_run_exports(
    output_dir: Path,
    config: dict[str, Any],
    summary: dict[str, Any],
    *,
    run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write processing_log.json to folder 00 (run_summary stays at output root only)."""
    admin_paths = resolve_admin_artifact_paths(output_dir, config)
    processing_log_path = admin_paths.processing_log
    ctx = dict(run_context or {})
    ctx.setdefault("finished_at", utc_now_iso())

    payload = build_processing_log(summary=summary, run_context=ctx)
    write_processing_log(processing_log_path, payload)
    summary["processing_log"] = str(processing_log_path)
    _maybe_copy_to_root(processing_log_path, output_dir, config)

    summary["admin_folder"] = str(admin_paths.admin_dir)
    summary["admin_artifact_count"] = sum(
        1 for path in admin_paths.admin_dir.iterdir() if path.is_file()
    )
    return summary
