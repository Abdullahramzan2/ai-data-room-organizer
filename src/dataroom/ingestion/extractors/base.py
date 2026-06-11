"""Base extractor interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from dataroom.ingestion.models import ExtractedDocument, FileMetadata
from dataroom.ocr.tesseract import TesseractOcr


class BaseExtractor(ABC):
    """Extract text and metadata from a single file."""

    extensions: set[str] = set()

    def __init__(self, ocr: TesseractOcr | None = None, max_text_chars: int = 500_000):
        self.ocr = ocr
        self.max_text_chars = max_text_chars

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() in self.extensions

    @abstractmethod
    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        raise NotImplementedError

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_text_chars:
            return text
        return text[: self.max_text_chars]

    def _apply_ocr_if_needed(self, doc: ExtractedDocument, path: Path, *, pdf: bool = False) -> ExtractedDocument:
        if not self.ocr or not self.ocr.config.enabled:
            return doc
        if not self.ocr.needs_ocr(doc.text_content):
            return doc
        if not self.ocr.is_available():
            doc.warnings.append(
                "OCR requested but Tesseract is not installed. "
                "Install Tesseract OCR and add it to PATH, or set ocr.tesseract_cmd in config/default.yaml"
            )
            if not doc.text_content.strip():
                from dataroom.ingestion.models import ExtractionMethod

                doc.extraction_method = ExtractionMethod.FAILED
            return doc
        try:
            if pdf:
                ocr_text, page_count = self.ocr.ocr_pdf(path)
                if doc.metadata.page_count is None:
                    doc.metadata.page_count = page_count
            else:
                ocr_text = self.ocr.ocr_image_path(path)
            doc.ocr_text = self._truncate(ocr_text)
            doc.ocr_applied = True
            from dataroom.ingestion.models import ExtractionMethod

            if doc.text_content.strip():
                doc.extraction_method = ExtractionMethod.HYBRID
            else:
                doc.extraction_method = ExtractionMethod.OCR
        except Exception as exc:
            doc.errors.append(f"OCR failed: {exc}")
        return doc
