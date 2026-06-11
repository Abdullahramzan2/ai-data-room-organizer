from pathlib import Path

from dataroom.ocr.tesseract import OcrConfig, TesseractOcr, resolve_tesseract_cmd


def test_needs_ocr_threshold():
    ocr = TesseractOcr(OcrConfig(min_native_text_chars=50))
    assert ocr.needs_ocr("short") is True
    assert ocr.needs_ocr("x" * 60) is False


def test_ocr_disabled():
    ocr = TesseractOcr(OcrConfig(enabled=False))
    assert ocr.needs_ocr("") is False
    assert ocr.is_available() is False


def test_resolve_tesseract_cmd_explicit_path(tmp_path):
    fake = tmp_path / "tesseract.exe"
    fake.write_text("stub", encoding="utf-8")
    assert resolve_tesseract_cmd(str(fake)) == str(fake)
