"""Rerun pipeline from cached ingestion/classification without re-OCR."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dataroom.config import load_app_config, load_taxonomy, resolve_project_root
from dataroom.corrections import apply_corrections, load_corrections_from_review_queue
from dataroom.duplicates import detect_duplicates, load_duplicate_config
from dataroom.duplicates.report import pairs_to_rows
from dataroom.duplicates.review_flags import apply_duplicate_review_flags
from dataroom.export.classification_log import file_content_fingerprint, utc_now_iso
from dataroom.organizer import organize_files
from dataroom.pipeline.cache import load_classification_cache, load_ingestion_cache
from dataroom.pipeline.outputs import export_pipeline_outputs, finalize_run_exports
from dataroom.pipeline.progress import RunProgressTracker


class RerunError(Exception):
    """Raised when rerun prerequisites are missing."""


def run_rerun(
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
    progress: RunProgressTracker | None = None,
) -> dict[str, Any]:
    """
    Re-organize and re-export from cached ingestion/classification data.

    Reads corrected_folder values from review_queue.csv and applies them
    without re-ingesting or re-classifying documents.
    """
    config = load_app_config(config_path)
    output_cfg = config.get("output", {})
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    tracker = progress
    if tracker is None:
        tracker = RunProgressTracker.start(
            output_dir,
            config=config,
            run_kind="rerun",
        )

    try:
        corrections_cfg = config.get("corrections", {}) or {}
        corrected_column = str(
            corrections_cfg.get("review_queue_corrected_folder_column", "corrected_folder")
        )

        ingestion_cache_path = output_dir / output_cfg.get(
            "ingestion_cache_file", "ingestion_cache.json"
        )
        classification_cache_path = output_dir / output_cfg.get(
            "classification_cache_file", "classification_cache.json"
        )
        review_path = output_dir / output_cfg.get("review_queue_file", "review_queue.csv")

        if not ingestion_cache_path.is_file():
            raise RerunError(f"Missing ingestion cache: {ingestion_cache_path}")
        if not classification_cache_path.is_file():
            raise RerunError(f"Missing classification cache: {classification_cache_path}")

        tracker.set_phase("loading_cache")
        ingestion_payload = load_ingestion_cache(ingestion_cache_path)
        classification_payload = load_classification_cache(classification_cache_path)

        ingestion_docs = ingestion_payload.get("documents", [])
        classification_results = [dict(row) for row in classification_payload.get("results", [])]
        skipped_files = [Path(p) for p in ingestion_payload.get("skipped_files", [])]
        failed_files = [
            (Path(item["path"]), item["error"])
            for item in ingestion_payload.get("failed_files", [])
        ]
        input_dir = Path(ingestion_payload.get("input_dir", ""))
        tracker.input_dir = str(input_dir)
        tracker.register_files([Path(row["source_path"]) for row in classification_results])
        for row in classification_results:
            tracker.file_classified(
                Path(row["source_path"]),
                category_folder=str(row.get("category_folder", "")),
                confidence=str(row.get("confidence", "")),
                needs_review=bool(row.get("needs_review")),
            )

        tracker.set_phase("applying_corrections")
        corrections = load_corrections_from_review_queue(
            review_path,
            column=corrected_column,
        )
        taxonomy = load_taxonomy(config=config)
        corrections_applied, correction_warnings = apply_corrections(
            classification_results,
            corrections,
            taxonomy,
        )
        for row in classification_results:
            if row.get("method") == "manual_correction":
                tracker.file_classified(
                    Path(row["source_path"]),
                    category_folder=str(row.get("category_folder", "")),
                    confidence=str(row.get("confidence", "")),
                    needs_review=bool(row.get("needs_review")),
                )

        tracker.set_phase("duplicates")
        duplicate_config = load_duplicate_config(config)
        duplicate_pairs = detect_duplicates(
            ingestion_docs,
            duplicate_config,
        )
        tracker.set_duplicate_pairs(pairs_to_rows(duplicate_pairs))
        apply_duplicate_review_flags(
            classification_results,
            duplicate_pairs,
            flag_for_review=duplicate_config.flag_for_review,
        )

        tracker.set_phase("organizing")
        organized = organize_files(
            classification_results,
            output_dir,
            taxonomy,
            rename=rename,
        )

        tracker.set_phase("exporting")
        root = resolve_project_root()
        config_fp_path = config_path or (root / "config" / "default.yaml")
        tax_rel = config.get("paths", {}).get("taxonomy_file", "taxonomy/real_estate_development.yaml")
        tax_path = root / tax_rel
        run_context = {
            "started_at": started_at,
            "rename": rename,
            "rerun": True,
            "taxonomy_name": str(taxonomy.get("name", "")),
            "taxonomy_version": str(taxonomy.get("version", "")),
            "taxonomy_fingerprint": file_content_fingerprint(tax_path),
            "config_fingerprint": file_content_fingerprint(config_fp_path),
        }
        summary = export_pipeline_outputs(
            output_dir=output_dir,
            config=config,
            ingestion_docs=ingestion_docs,
            classification_results=classification_results,
            organized=organized,
            duplicate_pairs=duplicate_pairs,
            skipped_files=skipped_files,
            failed_files=failed_files,
            rename=rename,
            input_dir=input_dir if str(input_dir) else None,
            persist_classification_cache=True,
            run_context=run_context,
            extra_summary={
                "rerun": True,
                "corrections_applied": corrections_applied,
                "correction_warnings": correction_warnings,
                "ingestion_cache": str(ingestion_cache_path),
                "rename": rename,
            },
        )
        run_context["finished_at"] = utc_now_iso()
        summary = finalize_run_exports(
            output_dir,
            config,
            summary,
            run_context=run_context,
        )
        (output_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        tracker.complete(summary)
        return summary
    except Exception as exc:
        tracker.fail(str(exc))
        raise
