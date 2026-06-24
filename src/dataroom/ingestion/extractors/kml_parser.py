"""Shared KML parsing for .kml and .kmz geographic files."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

_KML_NS_RE = re.compile(r"\{[^}]+\}")


def strip_kml_ns(tag: str) -> str:
    return _KML_NS_RE.sub("", tag)


def kml_element_text(elem: ET.Element | None) -> str:
    if elem is None:
        return ""
    parts = [elem.text or ""]
    for child in elem:
        if child.text:
            parts.append(child.text)
        if child.tail:
            parts.append(child.tail)
    return "".join(parts).strip()


def find_kml_children(parent: ET.Element, local_name: str) -> list[ET.Element]:
    return [c for c in parent.iter() if strip_kml_ns(c.tag) == local_name]


def parse_kml_content(kml_bytes: bytes) -> tuple[str, list[str], str]:
    """Return text_content, geo_signals, parse_status."""
    try:
        root = ET.fromstring(kml_bytes)
    except ET.ParseError as exc:
        return "", [], f"failed: {exc}"

    lines: list[str] = []
    signals: list[str] = []

    for doc in find_kml_children(root, "Document"):
        name = kml_element_text(next((c for c in doc if strip_kml_ns(c.tag) == "name"), None))
        desc = kml_element_text(next((c for c in doc if strip_kml_ns(c.tag) == "description"), None))
        if name:
            lines.append(f"Document: {name}")
            signals.append(f"document:{name}")
        if desc:
            lines.append(desc[:1000])
            signals.append(f"document_desc:{desc[:120]}")

    for folder in find_kml_children(root, "Folder"):
        name = kml_element_text(next((c for c in folder if strip_kml_ns(c.tag) == "name"), None))
        if name:
            lines.append(f"Folder: {name}")
            signals.append(f"folder:{name}")

    for pm in find_kml_children(root, "Placemark"):
        name = kml_element_text(next((c for c in pm if strip_kml_ns(c.tag) == "name"), None))
        desc = kml_element_text(next((c for c in pm if strip_kml_ns(c.tag) == "description"), None))
        if name:
            lines.append(f"Placemark: {name}")
            signals.append(f"placemark:{name}")
        if desc:
            lines.append(desc[:500])
            signals.append(f"desc:{desc[:120]}")

        for geom_name in ("Point", "LineString", "Polygon", "MultiGeometry"):
            if find_kml_children(pm, geom_name):
                lines.append(f"Geometry: {geom_name}")
                signals.append(f"geometry:{geom_name}")
                break

        coords = kml_element_text(next((c for c in pm.iter() if strip_kml_ns(c.tag) == "coordinates"), None))
        if coords:
            coord_short = coords.replace("\n", " ").strip()[:200]
            lines.append(f"Coordinates: {coord_short}")
            signals.append(f"coords:{coord_short[:80]}")

        for ext in find_kml_children(pm, "ExtendedData"):
            for data in find_kml_children(ext, "Data"):
                key = data.attrib.get("name", "")
                value = kml_element_text(next((c for c in data if strip_kml_ns(c.tag) == "value"), None))
                if key and value:
                    lines.append(f"{key}: {value[:200]}")
                    signals.append(f"extended:{key}")

        for simple in find_kml_children(pm, "SimpleData"):
            key = simple.attrib.get("name", "")
            value = kml_element_text(simple)
            if key and value:
                lines.append(f"{key}: {value[:200]}")
                signals.append(f"survey:{key}")

    for overlay in find_kml_children(root, "GroundOverlay"):
        name = kml_element_text(next((c for c in overlay if strip_kml_ns(c.tag) == "name"), None))
        if name:
            lines.append(f"Ground overlay: {name}")
            signals.append(f"overlay:{name}")

    text = "\n".join(lines).strip()
    status = "success" if text else "partial"
    return text, signals, status
