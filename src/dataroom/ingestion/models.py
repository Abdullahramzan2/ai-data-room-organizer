"""Data models for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class ExtractionMethod(str, Enum):
    NATIVE = "native"
    OCR = "ocr"
    HYBRID = "hybrid"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class FileMetadata:
    """Filesystem and format metadata for a source document."""

    source_path: Path
    file_name: str
    extension: str
    file_size: int
    created_at: datetime | None = None
    modified_at: datetime | None = None
    page_count: int | None = None


@dataclass
class ExtractedDocument:
    """Text and metadata extracted from a single source file."""

    metadata: FileMetadata
    text_content: str = ""
    ocr_text: str = ""
    extraction_method: ExtractionMethod = ExtractionMethod.SKIPPED
    ocr_applied: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __init__(
        self,
        metadata: FileMetadata,
        text_content: str = "",
        ocr_text: str = "",
        extraction_method: ExtractionMethod = ExtractionMethod.SKIPPED,
        ocr_applied: bool = False,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.metadata = metadata
        self.text_content = text_content
        self.ocr_text = ocr_text
        self.extraction_method = extraction_method
        self.ocr_applied = ocr_applied
        self.errors = errors if errors is not None else []
        self.warnings = warnings if warnings is not None else []
        self.extra = extra if extra is not None else {}

    @property
    def combined_text(self) -> str:
        """Full searchable text: native extraction plus OCR supplement."""
        parts = [self.text_content.strip(), self.ocr_text.strip()]
        return "\n\n".join(p for p in parts if p)

    @property
    def char_count(self) -> int:
        return len(self.combined_text)

    def to_dict(self) -> dict[str, Any]:
        meta = self.metadata
        return {
            "source_path": str(meta.source_path),
            "file_name": meta.file_name,
            "extension": meta.extension,
            "file_size": meta.file_size,
            "created_at": meta.created_at.isoformat() if meta.created_at else None,
            "modified_at": meta.modified_at.isoformat() if meta.modified_at else None,
            "page_count": meta.page_count,
            "text_content": self.text_content,
            "ocr_text": self.ocr_text,
            "combined_text": self.combined_text,
            "char_count": self.char_count,
            "extraction_method": self.extraction_method.value,
            "ocr_applied": self.ocr_applied,
            "errors": self.errors,
            "warnings": self.warnings,
            "extra": self.extra,
        }


@dataclass
class IngestionResult:
    """Aggregate result of scanning and extracting a folder batch."""

    documents: list[ExtractedDocument] = field(default_factory=list)
    skipped_files: list[Path] = field(default_factory=list)
    failed_files: list[tuple[Path, str]] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return len(self.documents)

    @property
    def total_with_text(self) -> int:
        return sum(1 for d in self.documents if d.char_count > 0)
