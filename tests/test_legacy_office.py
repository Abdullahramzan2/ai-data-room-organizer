from pathlib import Path
from unittest.mock import patch

from docx import Document

from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConverter
from dataroom.ingestion.extractors.office import DocExtractor, PptExtractor
from dataroom.ingestion.models import ExtractionMethod
from dataroom.ocr.tesseract import OcrConfig, TesseractOcr


def _make_docx(path: Path, text: str) -> Path:
    docx_path = path / "converted.docx"
    document = Document()
    document.add_paragraph(text)
    document.save(docx_path)
    return docx_path


def _make_pptx(path: Path, text: str) -> Path:
    from pptx import Presentation

    pptx_path = path / "converted.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = text
    prs.save(pptx_path)
    return pptx_path


def test_legacy_doc_via_libreoffice_conversion(tmp_path: Path):
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"fake-doc-content")

    converter = LegacyOfficeConverter()
    converted = _make_docx(tmp_path, "Legacy land control PSA content")

    with patch.object(converter, "_convert_via_libreoffice", return_value=converted):
        result = converter.extract_doc(source, max_chars=10_000)

    assert result.method == "libreoffice_docx"
    assert "land control PSA" in result.text
    assert not result.errors


def test_legacy_ppt_via_libreoffice_conversion(tmp_path: Path):
    source = tmp_path / "legacy.ppt"
    source.write_bytes(b"fake-ppt-content")

    converter = LegacyOfficeConverter()
    converted = _make_pptx(tmp_path, "Wetlands USACE overview")

    with patch.object(converter, "_convert_via_libreoffice", return_value=converted):
        result = converter.extract_ppt(source, max_chars=10_000)

    assert result.method == "libreoffice_pptx"
    assert "Wetlands USACE" in result.text
    assert result.page_count == 1
    assert not result.errors


def test_legacy_doc_via_antiword(tmp_path: Path):
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"fake-doc-content")

    converter = LegacyOfficeConverter()

    with patch.object(converter, "_convert_via_libreoffice", return_value=None), patch.object(
        converter, "_convert_via_com", return_value=None
    ), patch.object(
        converter, "_extract_via_cli_tool", side_effect=[None, "Recovered via catdoc text"]
    ):
        result = converter.extract_doc(source, max_chars=10_000)

    assert result.method == "catdoc"
    assert "Recovered via catdoc" in result.text


def test_legacy_doc_ocr_fallback(tmp_path: Path):
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"fake-doc-content")

    ocr = TesseractOcr(OcrConfig(enabled=True))
    converter = LegacyOfficeConverter(ocr=ocr)

    with patch.object(converter, "_convert_via_libreoffice", return_value=None), patch.object(
        converter, "_convert_via_com", return_value=None
    ), patch.object(converter, "_extract_via_cli_tool", return_value=None), patch.object(
        converter, "_ocr_via_pdf", return_value="OCR extracted correspondence"
    ):
        result = converter.extract_doc(source, max_chars=10_000)

    assert result.method == "libreoffice_pdf_ocr"
    assert "OCR extracted" in result.text


def test_legacy_doc_failure_lists_attempts(tmp_path: Path):
    source = tmp_path / "legacy.doc"
    source.write_bytes(b"fake-doc-content")

    converter = LegacyOfficeConverter(ocr=TesseractOcr(OcrConfig(enabled=False)))

    with patch.object(converter, "_convert_via_libreoffice", return_value=None), patch.object(
        converter, "_convert_via_com", return_value=None
    ), patch.object(converter, "_extract_via_cli_tool", return_value=None):
        result = converter.extract_doc(source, max_chars=10_000)

    assert result.text == ""
    assert result.errors
    assert "Could not extract .doc text" in result.errors[0]


def test_doc_extractor_uses_legacy_pipeline(tmp_path: Path):
    source = tmp_path / "sample.doc"
    source.write_bytes(b"fake-doc")

    from dataroom.ingestion.extractors.legacy_office import LegacyExtractionResult
    from dataroom.ingestion.models import FileMetadata
    from dataroom.ingestion.scanner import datetime_from_timestamp

    legacy = LegacyOfficeConverter()
    extractor = DocExtractor(legacy=legacy)

    stat = source.stat()
    file_meta = FileMetadata(
        source_path=source,
        file_name=source.name,
        extension=".doc",
        file_size=stat.st_size,
        created_at=datetime_from_timestamp(stat.st_ctime),
        modified_at=datetime_from_timestamp(stat.st_mtime),
    )

    mock_result = LegacyExtractionResult(
        text="Converted PSA document",
        method="libreoffice_docx",
    )
    with patch.object(legacy, "extract_doc", return_value=mock_result):
        doc = extractor.extract(source, file_meta)

    assert doc.text_content == "Converted PSA document"
    assert doc.extraction_method == ExtractionMethod.NATIVE
    assert doc.extra["legacy_extraction_method"] == "libreoffice_docx"


def test_ppt_extractor_uses_legacy_pipeline(tmp_path: Path):
    source = tmp_path / "sample.ppt"
    source.write_bytes(b"fake-ppt")

    from dataroom.ingestion.extractors.legacy_office import LegacyExtractionResult
    from dataroom.ingestion.models import FileMetadata
    from dataroom.ingestion.scanner import datetime_from_timestamp

    legacy = LegacyOfficeConverter()
    extractor = PptExtractor(legacy=legacy)

    stat = source.stat()
    file_meta = FileMetadata(
        source_path=source,
        file_name=source.name,
        extension=".ppt",
        file_size=stat.st_size,
        created_at=datetime_from_timestamp(stat.st_ctime),
        modified_at=datetime_from_timestamp(stat.st_mtime),
    )

    mock_result = LegacyExtractionResult(
        text="Slide deck about permitting",
        page_count=3,
        method="libreoffice_pptx",
    )
    with patch.object(legacy, "extract_ppt", return_value=mock_result):
        doc = extractor.extract(source, file_meta)

    assert "permitting" in doc.text_content
    assert doc.metadata.page_count == 3
    assert doc.extra["legacy_extraction_method"] == "libreoffice_pptx"
