"""End-to-end pipeline: ingest → classify → organize → export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataroom.classification import ClassificationEngine, load_classification_config
from dataroom.classification.engine import default_cache_dir
from dataroom.config import load_app_config, load_taxonomy
from dataroom.export import build_manifest_rows, write_manifest_csv, write_review_queue_csv
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.pipeline import run_ingestion
from dataroom.organizer import organize_files
from dataroom.ocr.tesseract import OcrConfig


def _document_from_row(row: dict[str, Any]) -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(row["source_path"]),
            file_name=row["file_name"],
            extension=row["extension"],
            file_size=row["file_size"],
        ),
        text_content=row.get("text_content", ""),
        ocr_text=row.get("ocr_text", ""),
        extraction_method=ExtractionMethod(row.get("extraction_method", "skipped")),
    )


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

    # 1. Ingest
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

    # 2. Classify
    taxonomy = load_taxonomy(config=config)
    engine = ClassificationEngine(
        taxonomy,
        load_classification_config(config),
        cache_dir=default_cache_dir(config),
    )
    classification_results = []
    for row in ingestion_docs:
        doc = _document_from_row(row)
        result = engine.classify_document(doc)
        classification_results.append(result.to_dict())

    # 3. Organize
    output_dir.mkdir(parents=True, exist_ok=True)
    organized = organize_files(
        classification_results,
        output_dir,
        taxonomy,
        rename=rename,
    )

    # 4. Export CSVs
    manifest_rows = build_manifest_rows(
        ingestion_docs,
        classification_results,
        output_dir,
        rename=rename,
    )
    manifest_path = output_dir / output_cfg.get("manifest_file", "manifest.csv")
    review_path = output_dir / output_cfg.get("review_queue_file", "review_queue.csv")
    write_manifest_csv(manifest_path, rows=manifest_rows)
    write_review_queue_csv(review_path, manifest_rows)

    api_used_count = sum(1 for r in classification_results if r.get("api_used"))
    review_count = sum(1 for r in manifest_rows if r.get("needs_review") == "true")

    summary = {
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "processed": len(ingestion_docs),
        "organized": len(organized),
        "review_queue_count": review_count,
        "api_used_count": api_used_count,
        "manifest": str(manifest_path),
        "review_queue": str(review_path),
    }

    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
