"""Route files to the appropriate extractor."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata
from dataroom.ingestion.scanner import build_metadata


class ExtractionRouter:
    """Select and run the extractor for a file extension."""

    def __init__(self, extractors: list[BaseExtractor]):
        self._by_extension: dict[str, BaseExtractor] = {}
        for extractor in extractors:
            for ext in extractor.extensions:
                self._by_extension[ext] = extractor

    def supported_extensions(self) -> set[str]:
        return set(self._by_extension.keys())

    def can_extract(self, path: Path) -> bool:
        return path.suffix.lower() in self._by_extension

    def extract(self, path: Path) -> ExtractedDocument:
        path = path.resolve()
        ext = path.suffix.lower()
        meta_dict = build_metadata(path)
        metadata = FileMetadata(
            source_path=path,
            file_name=path.name,
            extension=ext,
            file_size=meta_dict["file_size"],
            created_at=meta_dict["created_at"],
            modified_at=meta_dict["modified_at"],
        )

        extractor = self._by_extension.get(ext)
        if extractor is None:
            return ExtractedDocument(
                metadata=metadata,
                extraction_method=ExtractionMethod.SKIPPED,
                errors=[f"No extractor registered for extension: {ext}"],
            )

        return extractor.extract(path, metadata)
