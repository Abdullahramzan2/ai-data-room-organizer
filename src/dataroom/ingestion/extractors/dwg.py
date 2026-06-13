"""DWG CAD context extractor (local-only, metadata-based)."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata

_CAD_EXTENSIONS = {".dwg", ".dxf", ".dgn", ".rvt"}


class DwgExtractor(BaseExtractor):
    extensions = {".dwg"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "dwg_handler"
        doc.extra["parse_status"] = "partial"

        parent = path.parent
        siblings = sorted(
            f.name for f in parent.iterdir() if f.is_file() and f.resolve() != path.resolve()
        )
        companion_cad = [s for s in siblings if Path(s).suffix.lower() in _CAD_EXTENSIONS]
        companion_docs = [
            s
            for s in siblings
            if Path(s).suffix.lower() in {".pdf", ".txt", ".docx", ".xlsx", ".png", ".jpg"}
        ][:10]

        signals: list[str] = [
            f"filename:{metadata.file_name}",
            f"parent_folder:{parent.name}",
        ]
        if companion_cad:
            signals.append(f"cad_siblings:{','.join(companion_cad)}")
        if companion_docs:
            signals.append(f"doc_siblings:{','.join(companion_docs)}")

        doc.extra["extracted_cad_signals"] = signals

        lines = [
            f"CAD drawing file: {metadata.file_name}",
            f"Parent folder: {parent.name}",
        ]
        if companion_cad:
            lines.append(f"Related CAD files: {', '.join(companion_cad)}")
        if companion_docs:
            lines.append(f"Companion documents: {', '.join(companion_docs)}")

        doc.text_content = self._truncate("\n".join(lines))
        return doc
