"""Tesseract OCR integration for images and scanned PDFs."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from dataroom.paths import bundled_poppler_path, bundled_tesseract_cmd

logger = logging.getLogger(__name__)


@dataclass
class OcrConfig:
    enabled: bool = True
    language: str = "eng"
    pdf_dpi: int = 300
    min_native_text_chars: int = 50
    max_pdf_ocr_pages: int = 200
    classification_pdf_dpi: int = 150
    classification_pdf_ocr_pages: int = 2
    tesseract_cmd: str | None = None
    poppler_path: str | None = None


def ocr_config_from_app(config: dict) -> OcrConfig:
    """Build ``OcrConfig`` from ``config/default.yaml`` ocr section."""
    ocr_cfg = config.get("ocr", {}) or {}
    return OcrConfig(
        enabled=ocr_cfg.get("enabled", True),
        language=ocr_cfg.get("language", "eng"),
        pdf_dpi=int(ocr_cfg.get("pdf_dpi", 300)),
        min_native_text_chars=int(ocr_cfg.get("min_native_text_chars", 50)),
        max_pdf_ocr_pages=int(ocr_cfg.get("max_pdf_ocr_pages", 200)),
        classification_pdf_dpi=int(ocr_cfg.get("classification_pdf_dpi", 150)),
        classification_pdf_ocr_pages=int(ocr_cfg.get("classification_pdf_ocr_pages", 2)),
        tesseract_cmd=ocr_cfg.get("tesseract_cmd"),
        poppler_path=ocr_cfg.get("poppler_path"),
    )


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
    """Return Tesseract binary path from config, bundle, PATH, or common Windows locations."""
    if configured:
        path = Path(configured)
        return str(path) if path.is_file() else configured
    bundled = bundled_tesseract_cmd()
    if bundled:
        return bundled
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in _TESSERACT_WINDOWS_PATHS:
        if Path(candidate).is_file():
            return candidate
    return None


def resolve_poppler_path(configured: str | None) -> str | None:
    """Return Poppler bin directory for pdf2image (config, bundle, PATH, or Windows paths)."""
    if configured:
        path = Path(configured)
        if path.is_dir():
            return str(path)
        if (path / "pdftoppm.exe").is_file() or (path / "pdftoppm").is_file():
            return str(path)
        return configured
    bundled = bundled_poppler_path()
    if bundled:
        return bundled
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
        self.pdf_ocr_page_limit_hit = False

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

    def ocr_pdf(
        self,
        path: Path,
        *,
        dpi: int | None = None,
        max_pages: int | None = None,
    ) -> tuple[str, int]:
        """
        OCR a bounded page range of a PDF. Returns combined text and total page count.

        Only pages 1..N are rendered (via Poppler ``first_page`` / ``last_page``).
        Requires pdf2image and Poppler on PATH.
        """
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available on this system")

        try:
            from pdf2image import convert_from_path
        except ImportError as exc:
            raise RuntimeError("pdf2image is required for PDF OCR") from exc

        from dataroom.ocr.pdf_pages import pdf_page_count

        total_pages = pdf_page_count(path)
        render_dpi = dpi if dpi is not None else self.config.pdf_dpi
        page_limit = max_pages if max_pages is not None else self.config.max_pdf_ocr_pages
        last_page = total_pages
        if page_limit > 0:
            last_page = min(total_pages, page_limit)

        poppler_path = resolve_poppler_path(self.config.poppler_path)
        kwargs: dict = {
            "dpi": render_dpi,
            "first_page": 1,
            "last_page": last_page,
        }
        if poppler_path:
            kwargs["poppler_path"] = poppler_path

        try:
            pages = convert_from_path(str(path), **kwargs)
        except Exception as exc:
            hint = (
                "Install Poppler and add it to PATH, or set ocr.poppler_path in config/default.yaml"
            )
            raise RuntimeError(f"PDF to image conversion failed: {exc}. {hint}") from exc

        self.pdf_ocr_page_limit_hit = last_page < total_pages

        texts: list[str] = []
        for page in pages:
            texts.append(self.ocr_image(page))
        return "\n\n".join(texts), total_pages

    def ocr_pdf_for_classification(self, path: Path) -> tuple[str, int]:
        """OCR the first N pages at classification DPI (fast path for folder assignment)."""
        return self.ocr_pdf(
            path,
            dpi=self.config.classification_pdf_dpi,
            max_pages=self.config.classification_pdf_ocr_pages,
        )
