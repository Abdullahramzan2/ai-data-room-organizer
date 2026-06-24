"""GPX survey / track extractor."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.kml_parser import find_kml_children, kml_element_text, strip_kml_ns
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


def parse_gpx_content(gpx_bytes: bytes) -> tuple[str, list[str], str]:
    try:
        root = ET.fromstring(gpx_bytes)
    except ET.ParseError as exc:
        return "", [], f"failed: {exc}"

    lines: list[str] = []
    signals: list[str] = []

    for tag in ("name", "desc", "author", "email"):
        elem = next((c for c in root if strip_kml_ns(c.tag) == tag), None)
        value = kml_element_text(elem)
        if value:
            lines.append(f"{tag.title()}: {value[:300]}")
            signals.append(f"{tag}:{value[:80]}")

    for wpt in find_kml_children(root, "wpt"):
        name = kml_element_text(next((c for c in wpt if strip_kml_ns(c.tag) == "name"), None))
        desc = kml_element_text(next((c for c in wpt if strip_kml_ns(c.tag) == "desc"), None))
        lat = wpt.attrib.get("lat", "")
        lon = wpt.attrib.get("lon", "")
        label = name or "Waypoint"
        lines.append(f"Waypoint: {label}")
        signals.append(f"waypoint:{label[:80]}")
        if lat and lon:
            lines.append(f"Coordinates: {lon},{lat}")
            signals.append(f"coords:{lon},{lat}")
        if desc:
            lines.append(desc[:300])

    for trk in find_kml_children(root, "trk"):
        name = kml_element_text(next((c for c in trk if strip_kml_ns(c.tag) == "name"), None))
        if name:
            lines.append(f"Track: {name}")
            signals.append(f"track:{name[:80]}")

    for rte in find_kml_children(root, "rte"):
        name = kml_element_text(next((c for c in rte if strip_kml_ns(c.tag) == "name"), None))
        if name:
            lines.append(f"Route: {name}")
            signals.append(f"route:{name[:80]}")

    text = "\n".join(lines).strip()
    status = "success" if text else "partial"
    return text, signals, status


class GpxExtractor(BaseExtractor):
    extensions = {".gpx"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "gpx_parser"

        try:
            gpx_bytes = path.read_bytes()
        except OSError as exc:
            doc.errors.append(f"GPX read failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
            return doc

        text, signals, status = parse_gpx_content(gpx_bytes)
        doc.extra["parse_status"] = status
        doc.extra["extracted_geo_signals"] = signals

        if text:
            doc.text_content = self._truncate(text)
            if len(text) > self.max_text_chars:
                doc.warnings.append(f"GPX text truncated to {self.max_text_chars:,} characters")
        else:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.warnings.append("GPX contained no waypoints or tracks — filename fallback")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            doc.extra["parse_status"] = "partial"

        return doc
