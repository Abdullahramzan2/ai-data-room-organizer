"""DWG CAD context extractor with optional DXF conversion fallback."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.dxf import extract_dxf_text
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata

logger = logging.getLogger(__name__)

_CAD_EXTENSIONS = {".dwg", ".dxf", ".dgn", ".rvt"}
_DWG_VERSION_PREFIX = b"AC10"


def _read_dwg_version(path: Path) -> str | None:
    try:
        header = path.read_bytes()[:6]
    except OSError:
        return None
    if header.startswith(_DWG_VERSION_PREFIX):
        return header.decode("ascii", errors="replace")
    return None


def _try_dwgread_dxf(path: Path, tmp_dir: Path) -> Path | None:
    dwgread = shutil.which("dwgread")
    if not dwgread:
        return None
    out_path = tmp_dir / f"{path.stem}.dxf"
    try:
        result = subprocess.run(
            [dwgread, "-O", "DXF", "-o", str(out_path), str(path)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("dwgread failed for %s: %s", path, exc)
        return None
    if result.returncode != 0 or not out_path.is_file():
        return None
    return out_path


def _folder_context(path: Path) -> tuple[list[str], list[str], list[str]]:
    parent = path.parent
    siblings = sorted(
        f.name for f in parent.iterdir() if f.is_file() and f.resolve() != path.resolve()
    )
    companion_cad = [s for s in siblings if Path(s).suffix.lower() in _CAD_EXTENSIONS]
    companion_docs = [
        s
        for s in siblings
        if Path(s).suffix.lower() in {".pdf", ".txt", ".docx", ".xlsx", ".png", ".jpg", ".kml", ".kmz"}
    ][:10]
    signals: list[str] = [
        f"filename:{path.name}",
        f"parent_folder:{parent.name}",
    ]
    if companion_cad:
        signals.append(f"cad_siblings:{','.join(companion_cad)}")
    if companion_docs:
        signals.append(f"doc_siblings:{','.join(companion_docs)}")
    return companion_cad, companion_docs, signals


class DwgExtractor(BaseExtractor):
    extensions = {".dwg"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "dwg_handler"

        companion_cad, companion_docs, signals = _folder_context(path)
        doc.extra["extracted_cad_signals"] = list(signals)

        lines: list[str] = []
        version = _read_dwg_version(path)
        if version:
            lines.append(f"DWG version: {version}")
            signals.append(f"dwg_version:{version}")

        dxf_sources: list[tuple[str, Path]] = []
        sibling_dxf = path.with_suffix(".dxf")
        if sibling_dxf.is_file():
            dxf_sources.append(("sibling_dxf", sibling_dxf))

        with tempfile.TemporaryDirectory(prefix="dataroom_dwg_") as tmp:
            converted = _try_dwgread_dxf(path, Path(tmp))
            if converted:
                dxf_sources.append(("dwgread", converted))

            for source_name, dxf_path in dxf_sources:
                text, dxf_signals, status = extract_dxf_text(dxf_path, max_chars=self.max_text_chars)
                if text:
                    lines.append(f"Extracted via {source_name}:")
                    lines.append(text)
                    signals.extend(dxf_signals)
                    doc.extra["parse_status"] = "success"
                    doc.extra["legacy_extraction_method"] = source_name
                    doc.text_content = self._truncate("\n".join(lines))
                    doc.extra["extracted_cad_signals"] = signals
                    return doc
                if status.startswith("failed"):
                    doc.warnings.append(f"DXF conversion from {source_name} did not yield text")

        lines.extend(
            [
                f"CAD drawing file: {metadata.file_name}",
                f"Parent folder: {path.parent.name}",
            ]
        )
        if companion_cad:
            lines.append(f"Related CAD files: {', '.join(companion_cad)}")
        if companion_docs:
            lines.append(f"Companion documents: {', '.join(companion_docs)}")

        doc.extra["parse_status"] = "partial"
        doc.text_content = self._truncate("\n".join(lines))
        if not dxf_sources:
            doc.warnings.append(
                "DWG geometry text not extracted. Add a sibling .dxf, install LibreDWG dwgread, "
                "or rely on companion PDFs in the same folder."
            )
        return doc
