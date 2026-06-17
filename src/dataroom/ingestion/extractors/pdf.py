"""PDF text extraction with optional OCR fallback."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


class PdfExtractor(BaseExtractor):
    extensions = {".pdf"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        texts: list[str] = []

        try:
            with fitz.open(path) as pdf:
                doc.metadata.page_count = pdf.page_count
                for page in pdf:
                    page_text = page.get_text("text")
                    if isinstance(page_text, str):
                        texts.append(page_text)
        except Exception as exc:
            doc.errors.append(f"PDF native extraction failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED

        doc.text_content = self._truncate("\n".join(texts).strip())

        needs_scan = not doc.text_content.strip() or (
            self.ocr and self.ocr.needs_ocr(doc.text_content)
        )
        if needs_scan:
            doc = self._apply_ocr_if_needed(doc, path, pdf=True)
        elif not doc.text_content and not doc.ocr_applied:
            doc.warnings.append("No extractable text found in PDF")

        if doc.extraction_method == ExtractionMethod.NATIVE and doc.ocr_applied:
            doc.extraction_method = ExtractionMethod.HYBRID

        return doc
