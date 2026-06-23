"""Rerun pipeline from cached ingestion/classification without re-OCR."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.config import load_app_config, load_taxonomy
from dataroom.corrections import apply_corrections, load_corrections_from_review_queue
from dataroom.duplicates import detect_duplicates, load_duplicate_config
from dataroom.organizer import organize_files
from dataroom.pipeline.cache import load_classification_cache, load_ingestion_cache
from dataroom.pipeline.outputs import export_pipeline_outputs


class RerunError(Exception):
    """Raised when rerun prerequisites are missing."""


def run_rerun(
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
) -> dict[str, Any]:
    """
    Re-organize and re-export from cached ingestion/classification data.

    Reads corrected_folder values from review_queue.csv and applies them
    without re-ingesting or re-classifying documents.
    """
    config = load_app_config(config_path)
    output_cfg = config.get("output", {})
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

    duplicate_pairs = detect_duplicates(
        ingestion_docs,
        load_duplicate_config(config),
    )
    organized = organize_files(
        classification_results,
        output_dir,
        taxonomy,
        rename=rename,
    )

    return export_pipeline_outputs(
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
        extra_summary={
            "rerun": True,
            "corrections_applied": corrections_applied,
            "correction_warnings": correction_warnings,
            "ingestion_cache": str(ingestion_cache_path),
        },
    )
