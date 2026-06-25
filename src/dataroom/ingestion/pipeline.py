"""End-to-end ingestion: scan folder, extract text, apply OCR where needed."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Literal

from dataroom.ingestion.extractors import LegacyOfficeConfig, build_extractors
from dataroom.ingestion.models import ExtractedDocument, IngestionResult
from dataroom.ingestion.router import ExtractionRouter
from dataroom.ingestion.scanner import scan_folder
from dataroom.ocr.tesseract import OcrConfig, TesseractOcr

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, Path], None]
IngestOutcome = Literal["ingested", "failed", "skipped"]
IngestCompleteCallback = Callable[[Path, IngestOutcome, str], None]
IngestDocCompleteCallback = Callable[[Path, IngestOutcome, str, ExtractedDocument | None], None]


def build_ingestion_router(
    *,
    ocr_config: OcrConfig | None = None,
    legacy_office_config: LegacyOfficeConfig | None = None,
    max_text_chars: int = 500_000,
) -> ExtractionRouter:
    ocr = TesseractOcr(ocr_config or OcrConfig())
    return ExtractionRouter(
        build_extractors(
            ocr=ocr,
            max_text_chars=max_text_chars,
            legacy_office_config=legacy_office_config,
        )
    )


def ingest_path(
    router: ExtractionRouter,
    path: Path,
    *,
    max_file_size_bytes: int = 0,
) -> tuple[IngestOutcome, ExtractedDocument | None, str]:
    """Extract text from a single file."""
    if max_file_size_bytes and path.stat().st_size > max_file_size_bytes:
        logger.info("Skipped oversized file: %s", path)
        return "skipped", None, "File exceeds size limit"

    if not router.can_extract(path):
        return "skipped", None, "Unsupported file type"

    try:
        doc = router.extract(path)
        if doc.errors and doc.extraction_method.value == "failed":
            error = "; ".join(doc.errors)
            return "failed", doc, error
        return "ingested", doc, ""
    except Exception as exc:
        logger.exception("Failed to process %s", path)
        return "failed", None, str(exc)


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
    router = build_ingestion_router(
        ocr_config=ocr_config,
        legacy_office_config=legacy_office_config,
        max_text_chars=max_text_chars,
    )

    files = scan_folder(input_dir, supported_extensions, recursive=recursive)
    result = IngestionResult()
    total = len(files)

    for index, path in enumerate(files, start=1):
        if on_progress:
            on_progress(index, total, path)

        outcome, doc, error = ingest_path(
            router,
            path,
            max_file_size_bytes=max_file_size_bytes,
        )
        if outcome == "skipped":
            result.skipped_files.append(path)
            if on_file_complete:
                on_file_complete(path, "skipped", error)
        elif outcome == "failed":
            result.failed_files.append((path, error))
            if on_file_complete:
                on_file_complete(path, "failed", error)
            if doc is not None:
                result.documents.append(doc)
        else:
            if on_file_complete:
                on_file_complete(path, "ingested", "")
            if doc is not None:
                result.documents.append(doc)

    return result


def run_ingestion_from_files(
    files: list[Path],
    *,
    ocr_config: OcrConfig | None = None,
    legacy_office_config: LegacyOfficeConfig | None = None,
    max_file_size_bytes: int = 0,
    max_text_chars: int = 500_000,
    max_workers: int = 1,
    on_progress: ProgressCallback | None = None,
    on_file_complete: IngestCompleteCallback | None = None,
) -> IngestionResult:
    """Ingest a pre-scanned file list, optionally in parallel."""
    router = build_ingestion_router(
        ocr_config=ocr_config,
        legacy_office_config=legacy_office_config,
        max_text_chars=max_text_chars,
    )
    result = IngestionResult()
    total = len(files)
    workers = max(1, min(max_workers, total or 1))

    def _process(index: int, path: Path) -> tuple[int, Path, IngestOutcome, ExtractedDocument | None, str]:
        if on_progress:
            on_progress(index, total, path)
        outcome, doc, error = ingest_path(
            router,
            path,
            max_file_size_bytes=max_file_size_bytes,
        )
        return index, path, outcome, doc, error

    if workers == 1:
        indexed = [(index, path) for index, path in enumerate(files, start=1)]
        for index, path in indexed:
            _, path, outcome, doc, error = _process(index, path)
            _record_ingest_outcome(result, path, outcome, doc, error, on_file_complete)
        return result

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_process, index, path): path
            for index, path in enumerate(files, start=1)
        }
        for future in as_completed(futures):
            _, path, outcome, doc, error = future.result()
            _record_ingest_outcome(result, path, outcome, doc, error, on_file_complete)

    return result


def _record_ingest_outcome(
    result: IngestionResult,
    path: Path,
    outcome: IngestOutcome,
    doc: ExtractedDocument | None,
    error: str,
    on_file_complete: IngestCompleteCallback | None,
) -> None:
    if outcome == "skipped":
        result.skipped_files.append(path)
        if on_file_complete:
            on_file_complete(path, "skipped", error)
        return
    if outcome == "failed":
        result.failed_files.append((path, error))
        if on_file_complete:
            on_file_complete(path, "failed", error)
        if doc is not None:
            result.documents.append(doc)
        return
    if on_file_complete:
        on_file_complete(path, "ingested", "")
    if doc is not None:
        result.documents.append(doc)
