"""KMZ geographic extractors."""

from __future__ import annotations

import zipfile
from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.kml_parser import parse_kml_content
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


def read_kml_from_kmz(path: Path) -> bytes | None:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not names:
                return None
            target = "doc.kml" if "doc.kml" in names else names[0]
            return zf.read(target)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None


def extract_kml_bytes(
    kml_bytes: bytes,
    *,
    file_name: str,
    handler: str,
    max_chars: int,
) -> tuple[ExtractedDocument, FileMetadata]:
    """Parse KML bytes into a minimal document (metadata filled by caller)."""
    meta = FileMetadata(
        source_path=Path(file_name),
        file_name=file_name,
        extension=Path(file_name).suffix.lower() or ".kml",
        file_size=len(kml_bytes),
    )
    doc = ExtractedDocument(metadata=meta, extraction_method=ExtractionMethod.NATIVE)
    doc.extra["file_type_handler"] = handler

    text, signals, status = parse_kml_content(kml_bytes)
    doc.extra["parse_status"] = status
    doc.extra["extracted_geo_signals"] = signals

    if text:
        doc.text_content = text[:max_chars]
        if len(text) > max_chars:
            doc.warnings.append(f"KML text truncated to {max_chars:,} characters")
    else:
        doc.extraction_method = ExtractionMethod.FAILED
        doc.warnings.append("KML contained no extractable features — filename fallback")
        doc.text_content = file_name.replace("_", " ").replace("-", " ")
        doc.extra["parse_status"] = "partial"

    return doc, meta


class KmzExtractor(BaseExtractor):
    extensions = {".kmz"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "kmz_parser"

        kml_bytes = read_kml_from_kmz(path)
        if kml_bytes is None:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.extra["parse_status"] = "failed"
            doc.extra["extracted_geo_signals"] = []
            doc.warnings.append("KMZ parse failed — using filename for classification")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            return doc

        parsed, _ = extract_kml_bytes(
            kml_bytes,
            file_name=metadata.file_name,
            handler="kmz_parser",
            max_chars=self.max_text_chars,
        )
        doc.text_content = parsed.text_content
        doc.warnings.extend(parsed.warnings)
        doc.extra.update(parsed.extra)
        doc.extraction_method = parsed.extraction_method
        return doc
