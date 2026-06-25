"""End-to-end ingestion: scan folder, extract text, apply OCR where needed."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Literal

from dataroom.ingestion.extractors import LegacyOfficeConfig, build_extractors
from dataroom.ingestion.models import IngestionResult
from dataroom.ingestion.router import ExtractionRouter
from dataroom.ingestion.scanner import scan_folder
from dataroom.ocr.tesseract import OcrConfig, TesseractOcr

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, Path], None]
IngestOutcome = Literal["ingested", "failed", "skipped"]
IngestCompleteCallback = Callable[[Path, IngestOutcome, str], None]


def run_ingestion(
    input_dir: Path,
    *,
    supported_extensions: list[str],
    recursive: bool = True,
    ocr_config: OcrConfig | None = None,
    legacy_office_config: LegacyOfficeConfig | None = None,
    max_file_size_bytes: int = 0,
    max_text_chars: int = 500_000,
    on_progress: ProgressCallback | None = None,
    on_file_complete: IngestCompleteCallback | None = None,
) -> IngestionResult:
    """
    Scan input_dir and extract text from every supported file.

    Returns an IngestionResult with per-file ExtractedDocument records.
    """
    ocr = TesseractOcr(ocr_config or OcrConfig())
    router = ExtractionRouter(
        build_extractors(
            ocr=ocr,
            max_text_chars=max_text_chars,
            legacy_office_config=legacy_office_config,
        )
    )

    files = scan_folder(input_dir, supported_extensions, recursive=recursive)
    result = IngestionResult()
    total = len(files)

    for index, path in enumerate(files, start=1):
        if on_progress:
            on_progress(index, total, path)

        if max_file_size_bytes and path.stat().st_size > max_file_size_bytes:
            result.skipped_files.append(path)
            logger.info("Skipped oversized file: %s", path)
            if on_file_complete:
                on_file_complete(path, "skipped", "File exceeds size limit")
            continue

        if not router.can_extract(path):
            result.skipped_files.append(path)
            if on_file_complete:
                on_file_complete(path, "skipped", "Unsupported file type")
            continue

        try:
            doc = router.extract(path)
            if doc.errors and doc.extraction_method.value == "failed":
                error = "; ".join(doc.errors)
                result.failed_files.append((path, error))
                if on_file_complete:
                    on_file_complete(path, "failed", error)
            else:
                if on_file_complete:
                    on_file_complete(path, "ingested", "")
            result.documents.append(doc)
        except Exception as exc:
            logger.exception("Failed to process %s", path)
            error = str(exc)
            result.failed_files.append((path, error))
            if on_file_complete:
                on_file_complete(path, "failed", error)

    return result
