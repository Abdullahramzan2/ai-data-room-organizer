"""End-to-end pipeline: ingest → classify → organize → export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.classification import ClassificationEngine
from dataroom.classification.engine import default_cache_dir
from dataroom.classification.runtime import build_classification_runtime
from dataroom.config import load_app_config, load_taxonomy
from dataroom.duplicates import detect_duplicates, load_duplicate_config
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
from dataroom.ingestion.hashing import sha256_file
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.pipeline import run_ingestion
from dataroom.organizer import organize_files
from dataroom.ocr.tesseract import OcrConfig
from dataroom.pipeline.cache import (
    build_ingestion_cache_payload,
    write_ingestion_cache,
)
from dataroom.pipeline.outputs import export_pipeline_outputs


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
) -> dict[str, Any]:
    """Run full data room pipeline. Original source files are never modified."""
    config = load_app_config(config_path)
    input_cfg = config.get("input", {})
    ocr_cfg = config.get("ocr", {})
    ingest_cfg = config.get("ingestion", {})
    legacy_cfg = config.get("legacy_office", {})
    output_cfg = config.get("output", {})
    duplicate_config = load_duplicate_config(config)

    ocr_config = OcrConfig(
        enabled=not no_ocr and ocr_cfg.get("enabled", True),
        language=ocr_cfg.get("language", "eng"),
        pdf_dpi=ocr_cfg.get("pdf_dpi", 300),
        min_native_text_chars=ocr_cfg.get("min_native_text_chars", 50),
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

    ingestion_result = run_ingestion(
        input_dir,
        supported_extensions=input_cfg.get("supported_extensions", []),
        recursive=not no_recursive and input_cfg.get("recursive", True),
        ocr_config=ocr_config,
        legacy_office_config=legacy_office_config,
        max_file_size_bytes=ingest_cfg.get("max_file_size_bytes", 0),
        max_text_chars=ingest_cfg.get("max_text_chars", 500_000),
    )
    ingestion_docs = [d.to_dict() for d in ingestion_result.documents]
    _attach_file_hashes(ingestion_docs)
    duplicate_pairs = detect_duplicates(ingestion_docs, duplicate_config)

    taxonomy = load_taxonomy(config=config)
    engine = ClassificationEngine(
        taxonomy,
        classification_config,
        cache_dir=default_cache_dir(config),
        settings=settings,
        reasoning_provider=reasoning_provider,
        guardrails=guardrails,
    )
    classification_results = []
    for row in ingestion_docs:
        doc = _document_from_row(row)
        result = engine.classify_document(doc)
        classification_results.append(result.to_dict())

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
        skipped_files=ingestion_result.skipped_files,
        failed_files=ingestion_result.failed_files,
        rename=rename,
        input_dir=input_dir,
        persist_classification_cache=persist_cache,
        extra_summary={
            "reasoning_provider": reasoning_provider.provider_id,
            "guardrails_external_api": guardrails.config.allow_external_api,
            "audit_log": str(guardrails.resolve_audit_path(output_dir) or ""),
            "ingestion_cache": str(ingestion_cache_path) if persist_cache else "",
            "rerun": False,
        },
    )
