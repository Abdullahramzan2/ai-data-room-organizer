"""Tests for pipelined ingestion + classification."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.pipeline import build_ingestion_router
from dataroom.ocr.tesseract import OcrConfig
from dataroom.pipeline.pipelined import run_pipelined_ingest_and_classify
from dataroom.pipeline.progress import RunProgressTracker


def _document_from_row(row: dict) -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(row["source_path"]),
            file_name=row["file_name"],
            extension=row["extension"],
            file_size=int(row.get("file_size") or 0),
        ),
        text_content=row.get("text_content", ""),
        ocr_text=row.get("ocr_text", ""),
        extraction_method=ExtractionMethod(row.get("extraction_method", "native")),
        extra=row.get("extra") or {},
    )


def test_pipelined_classifies_while_ingesting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    files = []
    for name in ("a.txt", "b.txt", "c.txt"):
        path = input_dir / name
        path.write_text(f"content of {name}", encoding="utf-8")
        files.append(path)

    tracker = RunProgressTracker.start(output_dir, input_dir=input_dir)
    tracker.register_files(files)
    tracker.begin_ingestion()

    classify_calls: list[str] = []

    def fake_classify(document: ExtractedDocument):
        classify_calls.append(document.metadata.file_name)
        result = MagicMock()
        result.category_folder = "01_Test"
        result.confidence = "high"
        result.needs_review = False
        result.to_dict = lambda: {
            "source_path": str(document.metadata.source_path),
            "category_folder": "01_Test",
            "confidence": "high",
            "needs_review": False,
        }
        return result

    engine = MagicMock()
    engine.classify_document.side_effect = fake_classify

    router = build_ingestion_router(ocr_config=OcrConfig(enabled=False))
    monkeypatch.setattr(
        "dataroom.pipeline.pipelined.build_ingestion_router",
        lambda **_: router,
    )

    result, classifications = run_pipelined_ingest_and_classify(
        files,
        tracker=tracker,
        engine=engine,
        document_from_row=_document_from_row,
        ocr_config=OcrConfig(enabled=False),
        legacy_office_config=MagicMock(),
        ingestion_workers=1,
        classification_workers=2,
    )

    assert len(result.documents) == 3
    assert len(classifications) == 3
    assert set(classify_calls) == {"a.txt", "b.txt", "c.txt"}

    progress = tracker.to_dict()
    statuses = {row["file_name"]: row["status"] for row in progress["files"]}
    assert all(status == "done" for status in statuses.values())
    assert all(row["category_folder"] == "01_Test" for row in progress["files"])
