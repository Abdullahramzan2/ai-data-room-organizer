"""Tests for ingestion char-budget early-stop behavior."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import append_text_within_budget
from dataroom.ingestion.extractors.pdf import PdfExtractor, extract_pdf_native_text
from dataroom.ingestion.models import FileMetadata


def test_append_text_within_budget_stops_at_limit():
    text, truncated = append_text_within_budget("", "a" * 50, 100)
    assert len(text) == 50
    assert truncated is False

    text, truncated = append_text_within_budget(text, "b" * 60, 100)
    assert len(text) == 100
    assert truncated is True


def test_extract_pdf_native_text_stops_early():
    pages = ["page one text", "page two text", "page three text"]

    class FakePage:
        def __init__(self, value: str):
            self._value = value

        def get_text(self, kind: str) -> str:
            return self._value

    pdf = [FakePage(page) for page in pages]
    text, truncated = extract_pdf_native_text(pdf, max_chars=20)  # type: ignore[arg-type]
    assert len(text) <= 20
    assert truncated is True
    assert text.startswith("page one")


def test_pdf_extractor_warns_when_truncated(monkeypatch, tmp_path: Path):
    pdf_path = tmp_path / "large.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    class FakePage:
        def get_text(self, kind: str) -> str:
            return "x" * 5000

    class FakePdf:
        page_count = 50

        def __iter__(self):
            for _ in range(50):
                yield FakePage()

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("dataroom.ingestion.extractors.pdf.fitz.open", lambda _path: FakePdf())

    extractor = PdfExtractor(ocr=None, max_text_chars=10_000)
    doc = extractor.extract(
        pdf_path,
        FileMetadata(source_path=pdf_path, file_name="large.pdf", extension=".pdf", file_size=1),
    )

    assert len(doc.text_content) == 10_000
    assert any("Large PDF" in warning for warning in doc.warnings)
    assert hasattr(extractor, "_apply_ocr_if_needed")


def test_read_docx_text_stops_early(tmp_path: Path):
    from docx import Document

    from dataroom.ingestion.extractors.office import read_docx_text

    path = tmp_path / "long.docx"
    document = Document()
    for index in range(200):
        document.add_paragraph(f"Paragraph {index} " + ("content " * 20))
    document.save(path)

    text, truncated = read_docx_text(path, max_chars=5_000)
    assert len(text) <= 5_000
    assert truncated is True
