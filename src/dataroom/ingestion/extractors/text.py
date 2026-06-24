"""Plain text file extractor."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata

_READ_CHUNK_BYTES = 65_536  # reserved for future streaming helpers


def read_text_head(path: Path, max_chars: int) -> tuple[str, bool]:
    """Read up to max_chars without loading the entire file into memory."""
    for encoding in ("utf-8", "utf-16", "latin-1", "cp1252"):
        try:
            with path.open("r", encoding=encoding, errors="strict") as handle:
                text = handle.read(max_chars + 1)
            truncated = len(text) > max_chars
            return text[:max_chars], truncated
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("text", b"", 0, 1, "unsupported encoding")


class TextExtractor(BaseExtractor):
    extensions = {".txt"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        try:
            text, was_truncated = read_text_head(path, self.max_text_chars)
            doc.text_content = text
            if was_truncated:
                doc.warnings.append(
                    f"Large text file — only the first {self.max_text_chars:,} characters were loaded"
                )
        except UnicodeDecodeError:
            doc.errors.append("Could not decode text file with supported encodings")
            doc.extraction_method = ExtractionMethod.FAILED
        except OSError as exc:
            doc.errors.append(f"Text file read failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
        return doc
