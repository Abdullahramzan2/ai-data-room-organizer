"""KMZ/KML geographic extractors."""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata

_KML_NS_RE = re.compile(r"\{[^}]+\}")


def _strip_ns(tag: str) -> str:
    return _KML_NS_RE.sub("", tag)


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _find_children(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return [c for c in parent.iter() if _strip_ns(c.tag) == local_name]


def _parse_kml_content(kml_bytes: bytes) -> tuple[str, list[str], str]:
    """Return text_content, geo_signals, parse_status."""
    try:
        root = ET.fromstring(kml_bytes)
    except ET.ParseError as exc:
        return "", [], f"failed: {exc}"

    placemarks = _find_children(root, "Placemark")
    folders = _find_children(root, "Folder")
    lines: list[str] = []
    signals: list[str] = []

    for folder in folders:
        name = _text(next((c for c in folder if _strip_ns(c.tag) == "name"), None))
        if name:
            lines.append(f"Folder: {name}")
            signals.append(f"folder:{name}")

    for pm in placemarks:
        name = _text(next((c for c in pm if _strip_ns(c.tag) == "name"), None))
        desc = _text(next((c for c in pm if _strip_ns(c.tag) == "description"), None))
        coords = _text(next((c for c in pm.iter() if _strip_ns(c.tag) == "coordinates"), None))
        if name:
            lines.append(f"Placemark: {name}")
            signals.append(f"placemark:{name}")
        if desc:
            lines.append(desc[:500])
            signals.append(f"desc:{desc[:120]}")
        if coords:
            coord_short = coords.replace("\n", " ").strip()[:200]
            lines.append(f"Coordinates: {coord_short}")
            signals.append(f"coords:{coord_short[:80]}")

    text = "\n".join(lines).strip()
    status = "success" if text else "partial"
    return text, signals, status


def _read_kml_from_kmz(path: Path) -> bytes | None:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not names:
                return None
            # Prefer doc.kml
            target = "doc.kml" if "doc.kml" in names else names[0]
            return zf.read(target)
    except (zipfile.BadZipFile, KeyError, OSError):
        return None


class KmzExtractor(BaseExtractor):
    extensions = {".kmz"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "kmz_parser"

        kml_bytes = _read_kml_from_kmz(path)
        if kml_bytes is None:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.extra["parse_status"] = "failed"
            doc.extra["extracted_geo_signals"] = []
            doc.warnings.append("KMZ parse failed — using filename for classification")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            return doc

        text, signals, status = _parse_kml_content(kml_bytes)
        doc.extra["parse_status"] = status
        doc.extra["extracted_geo_signals"] = signals

        if text:
            doc.text_content = self._truncate(text)
        else:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.warnings.append("KML contained no placemarks — filename fallback")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            doc.extra["parse_status"] = "partial"

        return doc
