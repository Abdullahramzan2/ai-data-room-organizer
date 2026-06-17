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
    poppler_path: str | None = None


_TESSERACT_WINDOWS_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
)

_POPPLER_WINDOWS_DIRS = (
    r"C:\Program Files\poppler\Library\bin",
    r"C:\Program Files\poppler-24.08.0\Library\bin",
    r"C:\poppler\Library\bin",
    r"C:\ProgramData\chocolatey\lib\poppler\tools\Library\bin",
)


def resolve_tesseract_cmd(configured: str | None) -> str | None:
    """Return Tesseract binary path from config, PATH, or common Windows install locations."""
    if configured:
        path = Path(configured)
        return str(path) if path.is_file() else configured
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in _TESSERACT_WINDOWS_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def resolve_poppler_path(configured: str | None) -> str | None:
    """Return Poppler bin directory for pdf2image (PATH or common Windows locations)."""
    if configured:
        path = Path(configured)
        if path.is_dir():
            return str(path)
        if (path / "pdftoppm.exe").is_file() or (path / "pdftoppm").is_file():
            return str(path)
        return configured
    found = shutil.which("pdftoppm")
    if found:
        return str(Path(found).parent)
    for candidate in _POPPLER_WINDOWS_DIRS:
        if Path(candidate).is_dir():
            return candidate
    return None


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

            binary = resolve_tesseract_cmd(self.config.tesseract_cmd)
            if not binary or not Path(binary).is_file():
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
        pytesseract = self._pytesseract
        if pytesseract is None:
            raise RuntimeError("Tesseract OCR is not available on this system")
        return pytesseract.image_to_string(image, lang=self.config.language)

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

        poppler_path = resolve_poppler_path(self.config.poppler_path)
        kwargs: dict = {"dpi": self.config.pdf_dpi}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path

        try:
            pages = convert_from_path(str(path), **kwargs)
        except Exception as exc:
            hint = (
                "Install Poppler and add it to PATH, or set ocr.poppler_path in config/default.yaml"
            )
            raise RuntimeError(f"PDF to image conversion failed: {exc}. {hint}") from exc
        texts: list[str] = []
        for page in pages:
            texts.append(self.ocr_image(page))
        return "\n\n".join(texts), len(pages)
