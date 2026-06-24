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
    write_errors_report_csv,
    write_html_index,
    write_manifest_csv,
    write_manifest_xlsx,
    write_review_queue_csv,
)
from dataroom.export.admin_outputs import admin_folder_name, mirror_admin_artifacts
from dataroom.export.classification_log import (
    build_classification_log_rows,
    build_processing_log,
    utc_now_iso,
    write_classification_log_csv,
    write_processing_log,
)
from dataroom.duplicates import write_duplicate_report_csv
from dataroom.organizer.models import OrganizeResult
from dataroom.pipeline.cache import (
    build_classification_cache_payload,
    write_classification_cache,
)


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
    manifest_path = output_dir / output_cfg.get("manifest_file", "manifest.csv")
    manifest_xlsx_path = output_dir / output_cfg.get("manifest_xlsx_file", "manifest.xlsx")
    review_path = output_dir / output_cfg.get("review_queue_file", "review_queue.csv")
    errors_path = output_dir / output_cfg.get("errors_report_file", "errors_report.csv")
    duplicate_path = output_dir / output_cfg.get("duplicate_report_file", "duplicate_report.csv")
    index_html_path = output_dir / output_cfg.get("index_html_file", "index.html")
    classification_log_path = output_dir / output_cfg.get(
        "classification_log_file", "classification_log.csv"
    )
    classification_cache_path = output_dir / output_cfg.get(
        "classification_cache_file", "classification_cache.json"
    )

    write_manifest_csv(manifest_path, rows=manifest_rows)
    write_manifest_xlsx(manifest_xlsx_path, manifest_rows)
    write_review_queue_csv(review_path, manifest_rows)
    write_duplicate_report_csv(duplicate_path, duplicate_pairs)
    write_html_index(
        index_html_path,
        manifest_rows,
        link_mode=str(output_cfg.get("index_link_mode", "original")),
        output_dir=output_dir,
    )

    error_rows = build_ingestion_error_rows(skipped_files, failed_files)
    error_rows.extend(build_organize_error_rows(organized))
    write_errors_report_csv(errors_path, error_rows)

    log_timestamp = str((run_context or {}).get("started_at") or utc_now_iso())
    classification_log_rows = build_classification_log_rows(
        manifest_rows,
        timestamp=log_timestamp,
    )
    write_classification_log_csv(classification_log_path, classification_log_rows)

    if persist_classification_cache:
        write_classification_cache(
            classification_cache_path,
            build_classification_cache_payload(classification_results),
        )

    api_used_count = sum(1 for r in classification_results if r.get("api_used"))
    review_count = sum(1 for r in manifest_rows if r.get("needs_review") == "true")
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
        "manifest_xlsx": str(manifest_xlsx_path),
        "review_queue": str(review_path),
        "errors_report": str(errors_path),
        "duplicate_report": str(duplicate_path),
        "duplicate_pair_count": len(duplicate_pairs),
        "index_html": str(index_html_path),
        "classification_log": str(classification_log_path),
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
    """Write processing_log.json and mirror admin artifacts after run_summary is final."""
    output_cfg = config.get("output", {})
    processing_log_path = output_dir / output_cfg.get("processing_log_file", "processing_log.json")
    ctx = dict(run_context or {})
    ctx.setdefault("finished_at", utc_now_iso())

    payload = build_processing_log(summary=summary, run_context=ctx)
    write_processing_log(processing_log_path, payload)
    summary["processing_log"] = str(processing_log_path)

    run_summary_path = output_dir / "run_summary.json"
    artifact_paths = {
        "manifest": Path(str(summary.get("manifest", ""))),
        "manifest_xlsx": Path(str(summary.get("manifest_xlsx", ""))),
        "review_queue": Path(str(summary.get("review_queue", ""))),
        "duplicate_report": Path(str(summary.get("duplicate_report", ""))),
        "errors_report": Path(str(summary.get("errors_report", ""))),
        "index_html": Path(str(summary.get("index_html", ""))),
        "run_summary": run_summary_path,
        "classification_log": Path(str(summary.get("classification_log", ""))),
        "processing_log": processing_log_path,
    }
    mirrored = mirror_admin_artifacts(output_dir, config, artifact_paths)
    summary["admin_folder"] = str(output_dir / admin_folder_name(config))
    summary["admin_mirrored_count"] = len(mirrored)
    return summary
