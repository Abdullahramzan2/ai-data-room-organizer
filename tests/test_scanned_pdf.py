"""Tests for scanned PDF enrichment and bounded OCR."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from dataroom.ingestion.extractors.pdf import PdfExtractor
from dataroom.ingestion.extractors.scanned_pdf import build_scanned_pdf_context
from dataroom.ingestion.models import FileMetadata
from dataroom.ocr.tesseract import OcrConfig, TesseractOcr


def test_build_scanned_pdf_context_expands_ccr_and_reso():
    path = Path("RESO-20180925-21-CCR-East-Campus.pdf")
    text, signals = build_scanned_pdf_context(
        path,
        pdf_metadata={"creator": "Xerox ColorQube 9303"},
        page_count=28,
    )
    assert "covenants conditions restrictions" in text
    assert "resolution" in text
    assert "East" in text or "Campus" in text
    assert "Xerox ColorQube 9303" in text
    assert any("filename_tokens" in signal for signal in signals)


def test_build_scanned_pdf_context_skips_ocr_threshold():
    path = Path("RESO-20180925-21-CCR-East-Campus.pdf")
    text, _ = build_scanned_pdf_context(path, page_count=28)
    ocr = TesseractOcr(OcrConfig(min_native_text_chars=50))
    assert ocr.needs_ocr(text) is False


def test_ocr_pdf_uses_first_and_last_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 stub")

    captured: dict = {}

    def fake_convert(path: str, **kwargs):
        captured.update(kwargs)
        return [MagicMock(), MagicMock()]

    monkeypatch.setattr("pdf2image.convert_from_path", fake_convert)
    monkeypatch.setattr("dataroom.ocr.tesseract.resolve_poppler_path", lambda _: None)
    monkeypatch.setattr("dataroom.ocr.pdf_pages.pdf_page_count", lambda _: 28)

    ocr = TesseractOcr(
        OcrConfig(
            enabled=True,
            classification_pdf_dpi=150,
            classification_pdf_ocr_pages=2,
            tesseract_cmd=__import__("sys").executable,
        )
    )
    ocr._available = True
    ocr._pytesseract = MagicMock()
    ocr._pytesseract.image_to_string.return_value = "resolution covenants"

    text, total = ocr.ocr_pdf_for_classification(pdf_path)

    assert captured["first_page"] == 1
    assert captured["last_page"] == 2
    assert captured["dpi"] == 150
    assert total == 28
    assert "resolution" in text


def test_pdf_extractor_uses_enrichment_without_ocr(tmp_path: Path):
    pdf_path = tmp_path / "RESO-20180925-21-CCR-East-Campus.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 not a real pdf")

    metadata = FileMetadata(
        source_path=pdf_path,
        file_name=pdf_path.name,
        extension=".pdf",
        file_size=100,
    )

    extractor = PdfExtractor(ocr=TesseractOcr(OcrConfig(enabled=True)), max_text_chars=500_000)

    class FakePage:
        def get_text(self, _mode: str) -> str:
            return ""

    class FakePdf:
        page_count = 28
        metadata = {"creator": "Xerox ColorQube 9303"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter([FakePage()])

    with patch("dataroom.ingestion.extractors.pdf.fitz.open", return_value=FakePdf()):
        doc = extractor.extract(pdf_path, metadata)

    assert doc.extra.get("file_type_handler") == "scanned_pdf_handler"
    assert "covenants conditions restrictions" in doc.combined_text
    assert doc.ocr_applied is False
