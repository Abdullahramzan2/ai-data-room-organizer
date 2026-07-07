"""Standalone KML geographic extractor."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.kmz import extract_kml_bytes
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


class KmlExtractor(BaseExtractor):
    extensions = {".kml"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        try:
            kml_bytes = path.read_bytes()
        except OSError as exc:
            doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.FAILED)
            doc.errors.append(f"KML read failed: {exc}")
            return doc

        parsed, _ = extract_kml_bytes(
            kml_bytes,
            file_name=metadata.file_name,
            handler="kml_parser",
            max_chars=self.max_text_chars,
        )
        parsed.metadata = metadata
        return parsed
