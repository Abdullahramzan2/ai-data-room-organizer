"""GeoJSON survey / parcel map extractor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


def _flatten_properties(props: dict[str, Any], *, prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for key, value in props.items():
        label = f"{prefix}{key}" if not prefix else f"{prefix}.{key}"
        if isinstance(value, dict):
            rows.extend(_flatten_properties(value, prefix=label))
        elif value is not None and str(value).strip():
            rows.append((label, str(value)[:300]))
    return rows


def parse_geojson_content(payload: dict[str, Any]) -> tuple[str, list[str], str]:
    lines: list[str] = []
    signals: list[str] = []

    root_type = str(payload.get("type", ""))
    if root_type:
        lines.append(f"GeoJSON type: {root_type}")
        signals.append(f"type:{root_type}")

    name = str(payload.get("name", "") or "").strip()
    if name:
        lines.append(f"Collection: {name}")
        signals.append(f"collection:{name}")

    features = payload.get("features")
    if not isinstance(features, list):
        if root_type == "Feature":
            features = [payload]
        else:
            features = []

    for idx, feature in enumerate(features[:500], start=1):
        if not isinstance(feature, dict):
            continue
        geom = feature.get("geometry") or {}
        geom_type = str(geom.get("type", "") or "")
        props = feature.get("properties") or {}
        feature_name = ""
        if isinstance(props, dict):
            for key in ("name", "Name", "label", "title", "parcel_id", "PARCEL_ID", "id"):
                if props.get(key):
                    feature_name = str(props[key])
                    break

        header = feature_name or f"Feature {idx}"
        lines.append(f"Feature: {header}")
        signals.append(f"feature:{header[:80]}")
        if geom_type:
            lines.append(f"Geometry: {geom_type}")
            signals.append(f"geometry:{geom_type}")

        if isinstance(props, dict):
            for key, value in _flatten_properties(props)[:25]:
                lines.append(f"{key}: {value}")
                signals.append(f"prop:{key}")

    text = "\n".join(lines).strip()
    status = "success" if text else "partial"
    return text, signals, status


class GeoJsonExtractor(BaseExtractor):
    extensions = {".geojson", ".json"}

    def supports(self, path: Path) -> bool:
        return path.suffix.lower() == ".geojson"

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "geojson_parser"

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            doc.errors.append(f"GeoJSON parse failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
            doc.extra["parse_status"] = "failed"
            return doc

        if not isinstance(payload, dict):
            doc.errors.append("GeoJSON root must be an object")
            doc.extraction_method = ExtractionMethod.FAILED
            return doc

        text, signals, status = parse_geojson_content(payload)
        doc.extra["parse_status"] = status
        doc.extra["extracted_geo_signals"] = signals

        if text:
            doc.text_content = self._truncate(text)
            if len(text) > self.max_text_chars:
                doc.warnings.append(f"GeoJSON text truncated to {self.max_text_chars:,} characters")
        else:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.warnings.append("GeoJSON contained no features — filename fallback")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            doc.extra["parse_status"] = "partial"

        return doc
