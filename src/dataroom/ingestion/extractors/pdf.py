"""PDF text extraction with optional OCR fallback."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from dataroom.ingestion.extractors.base import BaseExtractor, append_text_within_budget
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


def extract_pdf_native_text(pdf: fitz.Document, max_chars: int) -> tuple[str, bool]:
    """Extract native PDF text, stopping once ``max_chars`` is reached."""
    text = ""
    truncated = False
    for page in pdf:
        page_text = page.get_text("text")
        if not isinstance(page_text, str) or not page_text.strip():
            continue
        text, page_truncated = append_text_within_budget(text, page_text, max_chars)
        if page_truncated:
            truncated = True
            break
    return text.strip(), truncated


class PdfExtractor(BaseExtractor):
    extensions = {".pdf"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        truncated = False

        try:
            with fitz.open(path) as pdf:
                doc.metadata.page_count = pdf.page_count
                doc.text_content, truncated = extract_pdf_native_text(pdf, self.max_text_chars)
        except Exception as exc:
            doc.errors.append(f"PDF native extraction failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED

        if truncated:
            doc.warnings.append(
                f"Large PDF — only the first {self.max_text_chars:,} characters were loaded"
            )

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
