"""Tesseract OCR integration for images and scanned PDFs."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class OcrConfig:
    enabled: bool = True
    language: str = "eng"
    pdf_dpi: int = 300
    min_native_text_chars: int = 50
    tesseract_cmd: str | None = None


class TesseractOcr:
    """Wrapper around pytesseract with PDF and image support."""

    def __init__(self, config: OcrConfig | None = None):
        self.config = config or OcrConfig()
        self._pytesseract = None
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        if not self.config.enabled:
            self._available = False
            return False
        try:
            import pytesseract

            if self.config.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_cmd
            else:
                binary = shutil.which("tesseract")
                if not binary:
                    self._available = False
                    return False
                pytesseract.pytesseract.tesseract_cmd = binary
            pytesseract.get_tesseract_version()
            self._pytesseract = pytesseract
            self._available = True
        except Exception as exc:
            logger.warning("Tesseract not available: %s", exc)
            self._available = False
        return self._available

    def needs_ocr(self, native_text: str) -> bool:
        if not self.config.enabled:
            return False
        return len(native_text.strip()) < self.config.min_native_text_chars

    def ocr_image(self, image: Image.Image) -> str:
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available on this system")
        return self._pytesseract.image_to_string(image, lang=self.config.language)

    def ocr_image_path(self, path: Path) -> str:
        with Image.open(path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            return self.ocr_image(img)

    def ocr_pdf(self, path: Path) -> tuple[str, int]:
        """
        OCR each page of a PDF. Returns combined text and page count.

        Requires pdf2image and a Poppler installation on the system PATH.
        """
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available on this system")

        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise RuntimeError("pdf2image is required for PDF OCR") from exc

        pages = convert_from_path(str(path), dpi=self.config.pdf_dpi)
        texts: list[str] = []
        for page in pages:
            texts.append(self.ocr_image(page))
        return "\n\n".join(texts), len(pages)
