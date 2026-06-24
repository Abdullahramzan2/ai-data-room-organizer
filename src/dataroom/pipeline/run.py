"""End-to-end pipeline: ingest → classify → organize → export."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dataroom.classification import ClassificationEngine
from dataroom.classification.engine import default_cache_dir
from dataroom.classification.runtime import build_classification_runtime
from dataroom.config import load_app_config, load_taxonomy, resolve_project_root
from dataroom.duplicates import detect_duplicates, load_duplicate_config
from dataroom.duplicates.report import pairs_to_rows
from dataroom.duplicates.review_flags import apply_duplicate_review_flags
from dataroom.export.classification_log import file_content_fingerprint, utc_now_iso
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
from dataroom.ingestion.hashing import sha256_file
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.pipeline import run_ingestion
from dataroom.ingestion.scanner import scan_folder
from dataroom.organizer import organize_files
from dataroom.ocr.tesseract import OcrConfig
from dataroom.pipeline.cache import (
    build_ingestion_cache_payload,
    write_ingestion_cache,
)
from dataroom.pipeline.outputs import export_pipeline_outputs, finalize_run_exports
from dataroom.pipeline.progress import RunProgressTracker


def _document_from_row(row: dict[str, Any]) -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(row["source_path"]),
            file_name=row["file_name"],
            extension=row["extension"],
            file_size=int(row.get("file_size") or 0),
        ),
        text_content=row.get("text_content", ""),
        ocr_text=row.get("ocr_text", ""),
        extraction_method=ExtractionMethod(row.get("extraction_method", "skipped")),
        extra=row.get("extra") or {},
    )


def _attach_file_hashes(ingestion_docs: list[dict[str, Any]]) -> None:
    for doc in ingestion_docs:
        source = Path(doc["source_path"])
        try:
            doc["file_hash"] = sha256_file(source)
        except OSError:
            doc["file_hash"] = ""


def run_pipeline(
    input_dir: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
    no_ocr: bool = False,
    no_recursive: bool = False,
    progress: RunProgressTracker | None = None,
) -> dict[str, Any]:
    """Run full data room pipeline. Original source files are never modified."""
    started = time.perf_counter()
    started_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    phase_started = started
    timings: dict[str, float] = {}

    config = load_app_config(config_path)
    tracker = progress
    if tracker is None:
        tracker = RunProgressTracker.start(output_dir, input_dir=input_dir, config=config)
    else:
        tracker.input_dir = str(input_dir)

    try:
        class_cfg = config.get("classification", {})
        from dataroom.models_setup import DEFAULT_EMBEDDING_MODEL, ensure_embedding_model

        tracker.set_phase("model_ready")
        ensure_embedding_model(str(class_cfg.get("embedding_model", DEFAULT_EMBEDDING_MODEL)), quiet=True)
        timings["model_ready_seconds"] = round(time.perf_counter() - phase_started, 2)
        phase_started = time.perf_counter()

        input_cfg = config.get("input", {})
        ocr_cfg = config.get("ocr", {})
        ingest_cfg = config.get("ingestion", {})
        legacy_cfg = config.get("legacy_office", {})
        output_cfg = config.get("output", {})
        duplicate_config = load_duplicate_config(config)
        supported_extensions = input_cfg.get("supported_extensions", [])
        recursive = not no_recursive and input_cfg.get("recursive", True)

        tracker.set_phase("scanning")
        scanned_files = scan_folder(input_dir, supported_extensions, recursive=recursive)
        tracker.register_files(scanned_files)

        ocr_config = OcrConfig(
            enabled=not no_ocr and ocr_cfg.get("enabled", True),
            language=ocr_cfg.get("language", "eng"),
            pdf_dpi=ocr_cfg.get("pdf_dpi", 300),
            min_native_text_chars=ocr_cfg.get("min_native_text_chars", 50),
            max_pdf_ocr_pages=int(ocr_cfg.get("max_pdf_ocr_pages", 200)),
            tesseract_cmd=ocr_cfg.get("tesseract_cmd"),
            poppler_path=ocr_cfg.get("poppler_path"),
        )
        legacy_office_config = LegacyOfficeConfig(
            libreoffice_cmd=legacy_cfg.get("libreoffice_cmd"),
            enable_com=legacy_cfg.get("enable_com", True),
            conversion_timeout=legacy_cfg.get("conversion_timeout", 120),
        )

        settings, guardrails, reasoning_provider, classification_config = build_classification_runtime(
            config,
            output_dir=output_dir,
        )

        def on_ingest_progress(index: int, total: int, path: Path) -> None:
            tracker.file_ingesting(path, index, total)

        ingestion_result = run_ingestion(
            input_dir,
            supported_extensions=supported_extensions,
            recursive=recursive,
            ocr_config=ocr_config,
            legacy_office_config=legacy_office_config,
            max_file_size_bytes=ingest_cfg.get("max_file_size_bytes", 0),
            max_text_chars=ingest_cfg.get("max_text_chars", 500_000),
            on_progress=on_ingest_progress,
        )
        for doc in ingestion_result.documents:
            tracker.file_ingested(doc.metadata.source_path)
        for path, error in ingestion_result.failed_files:
            tracker.file_failed(path, error)
        tracker.set_skipped_count(len(ingestion_result.skipped_files))

        ingestion_docs = [d.to_dict() for d in ingestion_result.documents]
        _attach_file_hashes(ingestion_docs)
        timings["ingestion_seconds"] = round(time.perf_counter() - phase_started, 2)
        phase_started = time.perf_counter()

        tracker.set_phase("duplicates")
        duplicate_pairs = detect_duplicates(ingestion_docs, duplicate_config)
        tracker.set_duplicate_pairs(pairs_to_rows(duplicate_pairs))
        timings["duplicates_seconds"] = round(time.perf_counter() - phase_started, 2)
        phase_started = time.perf_counter()

        taxonomy = load_taxonomy(config=config)
        engine = ClassificationEngine(
            taxonomy,
            classification_config,
            cache_dir=default_cache_dir(config),
            settings=settings,
            reasoning_provider=reasoning_provider,
            guardrails=guardrails,
        )

        def on_classifying(_index: int, _total: int, path: Path) -> None:
            tracker.file_classifying(path)

        def on_classified(_index: int, _total: int, result) -> None:
            tracker.file_classified(
                result.source_path,
                category_folder=result.category_folder,
                confidence=result.confidence,
                needs_review=result.needs_review,
            )

        documents = [_document_from_row(row) for row in ingestion_docs]
        classification_results = [
            result.to_dict()
            for result in engine.classify_batch(
                documents,
                on_classifying=on_classifying,
                on_classified=on_classified,
            )
        ]
        apply_duplicate_review_flags(
            classification_results,
            duplicate_pairs,
            flag_for_review=duplicate_config.flag_for_review,
        )
        timings["classification_seconds"] = round(time.perf_counter() - phase_started, 2)
        phase_started = time.perf_counter()

        output_dir.mkdir(parents=True, exist_ok=True)

        persist_cache = output_cfg.get("persist_ingestion_cache", True)
        ingestion_cache_path = output_dir / output_cfg.get(
            "ingestion_cache_file", "ingestion_cache.json"
        )
        classification_cache_path = output_dir / output_cfg.get(
            "classification_cache_file", "classification_cache.json"
        )
        if persist_cache:
            write_ingestion_cache(
                ingestion_cache_path,
                build_ingestion_cache_payload(
                    input_dir,
                    ingestion_docs,
                    skipped_files=ingestion_result.skipped_files,
                    failed_files=ingestion_result.failed_files,
                ),
            )

        tracker.set_phase("organizing")
        organized = organize_files(
            classification_results,
            output_dir,
            taxonomy,
            rename=rename,
        )
        timings["organize_seconds"] = round(time.perf_counter() - phase_started, 2)
        phase_started = time.perf_counter()

        tracker.set_phase("exporting")
        root = resolve_project_root()
        config_fp_path = config_path or (root / "config" / "default.yaml")
        tax_rel = config.get("paths", {}).get("taxonomy_file", "taxonomy/real_estate_development.yaml")
        tax_path = root / tax_rel
        run_context = {
            "started_at": started_at,
            "ocr_enabled": ocr_config.enabled,
            "recursive": recursive,
            "rename": rename,
            "taxonomy_name": str(taxonomy.get("name", "")),
            "taxonomy_version": str(taxonomy.get("version", "")),
            "taxonomy_fingerprint": file_content_fingerprint(tax_path),
            "config_fingerprint": file_content_fingerprint(config_fp_path),
            "reasoning_provider": reasoning_provider.provider_id,
        }
        summary = export_pipeline_outputs(
            output_dir=output_dir,
            config=config,
            ingestion_docs=ingestion_docs,
            classification_results=classification_results,
            organized=organized,
            duplicate_pairs=duplicate_pairs,
            skipped_files=ingestion_result.skipped_files,
            failed_files=ingestion_result.failed_files,
            rename=rename,
            input_dir=input_dir,
            persist_classification_cache=persist_cache,
            run_context=run_context,
            extra_summary={
                "reasoning_provider": reasoning_provider.provider_id,
                "guardrails_external_api": guardrails.config.allow_external_api,
                "audit_log": str(guardrails.resolve_audit_path(output_dir) or ""),
                "ingestion_cache": str(ingestion_cache_path) if persist_cache else "",
                "rerun": False,
                "rename": rename,
                "ocr_enabled": ocr_config.enabled,
                "recursive": recursive,
            },
        )
        timings["export_seconds"] = round(time.perf_counter() - phase_started, 2)
        timings["total_seconds"] = round(time.perf_counter() - started, 2)
        summary["timings"] = timings
        (output_dir / "run_summary.json").write_text(
            json.dumps(summary, indent=2),
            encoding="utf-8",
        )
        run_context["finished_at"] = utc_now_iso()
        run_context["timings"] = timings
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
