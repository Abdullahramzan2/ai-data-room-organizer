"""Image file extraction via OCR."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


class ImageExtractor(BaseExtractor):
    extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.OCR)
        if not self.ocr or not self.ocr.is_available():
            doc.errors.append("Image files require Tesseract OCR, which is not available")
            doc.extraction_method = ExtractionMethod.FAILED
            return doc
        try:
            doc.ocr_text = self._truncate(self.ocr.ocr_image_path(path))
            doc.ocr_applied = True
            if not doc.ocr_text.strip():
                doc.warnings.append("OCR returned no text for image")
        except Exception as exc:
            doc.errors.append(f"Image OCR failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
        return doc
