"""Overlapping ingestion and classification worker pools."""

from __future__ import annotations

import logging
import queue
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig
from dataroom.ingestion.models import ExtractedDocument, IngestionResult
from dataroom.ingestion.pipeline import build_ingestion_router, ingest_path
from dataroom.ocr.tesseract import OcrConfig
from dataroom.pipeline.progress import RunProgressTracker

if TYPE_CHECKING:
    from dataroom.classification.engine import ClassificationEngine

logger = logging.getLogger(__name__)

_SENTINEL = object()


def run_pipelined_ingest_and_classify(
    files: list[Path],
    *,
    tracker: RunProgressTracker,
    engine: ClassificationEngine,
    document_from_row: Callable[[dict[str, Any]], ExtractedDocument],
    ocr_config: OcrConfig,
    legacy_office_config: LegacyOfficeConfig,
    max_file_size_bytes: int = 0,
    max_text_chars: int = 500_000,
    ingestion_workers: int = 1,
    classification_workers: int = 2,
    on_ingest_progress: Callable[[int, int, Path], None] | None = None,
) -> tuple[IngestionResult, list[Any]]:
    """
    Ingest files and classify each one as soon as extraction finishes.

    Duplicate detection and organization still run after this returns.
    """
    result = IngestionResult()
    total = len(files)
    ordered_results: list[Any | None] = [None] * total
    results_lock = threading.Lock()
    classify_lock = threading.Lock()

    ingest_q: queue.Queue[tuple[int, Path] | object] = queue.Queue()
    classify_q: queue.Queue[tuple[int, dict[str, Any]] | object] = queue.Queue()

    router = build_ingestion_router(
        ocr_config=ocr_config,
        legacy_office_config=legacy_office_config,
        max_text_chars=max_text_chars,
    )

    def _ingestion_worker() -> None:
        while True:
            item = ingest_q.get()
            try:
                if item is _SENTINEL:
                    break
                index, path = item
                if on_ingest_progress:
                    on_ingest_progress(index, total, path)
                outcome, doc, error = ingest_path(
                    router,
                    path,
                    max_file_size_bytes=max_file_size_bytes,
                )
                if outcome == "skipped":
                    result.skipped_files.append(path)
                    tracker.file_skipped(path)
                elif outcome == "failed":
                    result.failed_files.append((path, error))
                    tracker.file_failed(path, error)
                    if doc is not None:
                        result.documents.append(doc)
                else:
                    assert doc is not None
                    result.documents.append(doc)
                    doc_dict = doc.to_dict()
                    tracker.file_classifying(path)
                    classify_q.put((index, doc_dict))
            finally:
                ingest_q.task_done()

    def _classification_worker() -> None:
        while True:
            item = classify_q.get()
            try:
                if item is _SENTINEL:
                    break
                index, doc_dict = item
                document = document_from_row(doc_dict)
                path = document.metadata.source_path
                with classify_lock:
                    classification = engine.classify_document(document)
                tracker.file_classified(
                    path,
                    category_folder=classification.category_folder,
                    confidence=classification.confidence,
                    needs_review=classification.needs_review,
                )
                with results_lock:
                    ordered_results[index] = classification
            finally:
                classify_q.task_done()

    ingest_worker_count = max(1, min(ingestion_workers, total or 1))
    classify_worker_count = max(1, min(classification_workers, total or 1))

    ingest_threads = [
        threading.Thread(target=_ingestion_worker, name=f"ingest-{i}", daemon=True)
        for i in range(ingest_worker_count)
    ]
    classify_threads = [
        threading.Thread(target=_classification_worker, name=f"classify-{i}", daemon=True)
        for i in range(classify_worker_count)
    ]

    for thread in ingest_threads + classify_threads:
        thread.start()

    for index, path in enumerate(files):
        ingest_q.put((index, path))

    for _ in range(ingest_worker_count):
        ingest_q.put(_SENTINEL)

    ingest_q.join()

    for _ in range(classify_worker_count):
        classify_q.put(_SENTINEL)

    classify_q.join()

    for thread in ingest_threads + classify_threads:
        thread.join(timeout=1.0)

    classification_results = [item for item in ordered_results if item is not None]
    return result, classification_results
