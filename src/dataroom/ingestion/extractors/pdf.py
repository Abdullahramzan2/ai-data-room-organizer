"""PDF text extraction with optional OCR fallback."""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

from dataroom.ingestion.extractors.base import BaseExtractor, append_text_within_budget
from dataroom.ingestion.extractors.scanned_pdf import build_scanned_pdf_context
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
        pdf_meta: dict[str, str | None] = {}

        try:
            with fitz.open(path) as pdf:
                doc.metadata.page_count = pdf.page_count
                doc.text_content, truncated = extract_pdf_native_text(pdf, self.max_text_chars)
                pdf_meta = {
                    key: pdf.metadata.get(key) for key in ("title", "author", "subject", "creator", "producer")
                }
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
            if not doc.text_content.strip():
                enriched, signals = build_scanned_pdf_context(
                    path,
                    pdf_metadata=pdf_meta,
                    page_count=doc.metadata.page_count,
                )
                doc.text_content = self._truncate(enriched)
                doc.extra["scanned_pdf_signals"] = signals
                doc.extra["file_type_handler"] = "scanned_pdf_handler"

            if self.ocr and self.ocr.needs_ocr(doc.text_content):
                doc = self._apply_pdf_ocr(doc, path)
            elif not doc.text_content.strip():
                doc.warnings.append("No extractable text found in PDF")
        elif not doc.text_content and not doc.ocr_applied:
            doc.warnings.append("No extractable text found in PDF")

        if doc.extraction_method == ExtractionMethod.NATIVE and doc.ocr_applied:
            doc.extraction_method = ExtractionMethod.HYBRID

        return doc

    def _apply_pdf_ocr(self, doc: ExtractedDocument, path: Path) -> ExtractedDocument:
        if not self.ocr or not self.ocr.config.enabled:
            return doc
        if not self.ocr.is_available():
            doc.warnings.append(
                "OCR requested but Tesseract is not installed. "
                "Install Tesseract OCR and add it to PATH, or set ocr.tesseract_cmd in config/default.yaml"
            )
            if not doc.text_content.strip():
                doc.extraction_method = ExtractionMethod.FAILED
            return doc
        try:
            ocr_text, page_count = self.ocr.ocr_pdf_for_classification(path)
            if doc.metadata.page_count is None:
                doc.metadata.page_count = page_count
            if self.ocr.pdf_ocr_page_limit_hit:
                limit = self.ocr.config.classification_pdf_ocr_pages
                doc.warnings.append(
                    f"Scanned PDF — OCR applied to first {limit} of {page_count} pages "
                    f"at {self.ocr.config.classification_pdf_dpi} DPI"
                )
            doc.ocr_text = self._truncate(ocr_text)
            doc.ocr_applied = True
            if doc.text_content.strip():
                doc.extraction_method = ExtractionMethod.HYBRID
            else:
                doc.extraction_method = ExtractionMethod.OCR
        except Exception as exc:
            doc.errors.append(f"OCR failed: {exc}")
        return doc
