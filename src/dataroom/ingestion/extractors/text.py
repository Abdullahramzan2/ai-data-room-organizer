"""Plain text file extractor."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


class TextExtractor(BaseExtractor):
    extensions = {".txt"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        for encoding in ("utf-8", "utf-16", "latin-1", "cp1252"):
            try:
                doc.text_content = self._truncate(path.read_text(encoding=encoding))
                return doc
            except UnicodeDecodeError:
                continue
        doc.errors.append("Could not decode text file with supported encodings")
        doc.extraction_method = ExtractionMethod.FAILED
        return doc
