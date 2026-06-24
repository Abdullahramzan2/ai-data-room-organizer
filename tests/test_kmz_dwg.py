"""Tests for KMZ, KML, GeoJSON, GPX, DXF, and DWG extractors."""

import json
import zipfile
from pathlib import Path

import pytest

from dataroom.ingestion.extractors.dwg import DwgExtractor
from dataroom.ingestion.extractors.geojson import GeoJsonExtractor, parse_geojson_content
from dataroom.ingestion.extractors.gpx import GpxExtractor, parse_gpx_content
from dataroom.ingestion.extractors.kml import KmlExtractor
from dataroom.ingestion.extractors.kml_parser import parse_kml_content
from dataroom.ingestion.extractors.kmz import KmzExtractor
from dataroom.ingestion.extractors.text import read_text_head
from dataroom.ingestion.models import FileMetadata

SAMPLE_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Wetland Exhibit</name>
    <Folder><name>Wetland Study</name></Folder>
    <Placemark>
      <name>Site Boundary</name>
      <description>USACE wetland delineation area</description>
      <ExtendedData>
        <Data name="parcel_id"><value>P-100</value></Data>
      </ExtendedData>
      <Point><coordinates>-98.5,29.4,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""


def _meta(path: Path) -> FileMetadata:
    return FileMetadata(
        source_path=path,
        file_name=path.name,
        extension=path.suffix.lower(),
        file_size=path.stat().st_size,
    )


def test_parse_kml_extracts_placemarks_and_extended_data():
    text, signals, status = parse_kml_content(SAMPLE_KML)
    assert status == "success"
    assert "Site Boundary" in text
    assert "USACE" in text
    assert "parcel_id" in text
    assert "Wetland Exhibit" in text
    assert any("placemark" in s.lower() for s in signals)


def test_kml_extractor_reads_standalone_file(tmp_path):
    kml_path = tmp_path / "survey.kml"
    kml_path.write_bytes(SAMPLE_KML)
    doc = KmlExtractor().extract(kml_path, _meta(kml_path))
    assert doc.extra["file_type_handler"] == "kml_parser"
    assert "Site Boundary" in doc.text_content


def test_kmz_extractor_parses_zip(tmp_path):
    kmz_path = tmp_path / "wetland_study.kmz"
    with zipfile.ZipFile(kmz_path, "w") as zf:
        zf.writestr("doc.kml", SAMPLE_KML)

    doc = KmzExtractor().extract(kmz_path, _meta(kmz_path))
    assert doc.extra["file_type_handler"] == "kmz_parser"
    assert doc.extra["parse_status"] == "success"
    assert "Site Boundary" in doc.text_content


def test_geojson_extractor_parses_features(tmp_path):
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Polygon"},
                "properties": {"name": "Parcel A", "parcel_id": "123"},
            }
        ],
    }
    path = tmp_path / "parcels.geojson"
    path.write_text(json.dumps(payload), encoding="utf-8")
    doc = GeoJsonExtractor().extract(path, _meta(path))
    assert "Parcel A" in doc.text_content
    assert "123" in doc.text_content


def test_parse_geojson_content_handles_feature_collection():
    text, signals, status = parse_geojson_content(
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"name": "Lot 1"},
                    "geometry": {"type": "Point"},
                }
            ],
        }
    )
    assert status == "success"
    assert "Lot 1" in text


def test_gpx_extractor_parses_waypoint(tmp_path):
    gpx = b"""<?xml version="1.0"?>
<gpx version="1.1">
  <metadata><name>Survey Track</name></metadata>
  <wpt lat="29.4" lon="-98.5"><name>Control Point</name><desc>Benchmark</desc></wpt>
</gpx>"""
    path = tmp_path / "survey.gpx"
    path.write_bytes(gpx)
    doc = GpxExtractor().extract(path, _meta(path))
    assert "Control Point" in doc.text_content
    assert "Benchmark" in doc.text_content


def test_parse_gpx_content():
    text, _, status = parse_gpx_content(
        b'<gpx><wpt lat="1" lon="2"><name>WP1</name></wpt></gpx>'
    )
    assert status == "success"
    assert "WP1" in text


def test_dwg_extractor_uses_sibling_dxf(tmp_path):
    pytest.importorskip("ezdxf")
    import ezdxf

    dwg = tmp_path / "site_plan.dwg"
    dwg.write_bytes(b"AC1032 fake")
    dxf_path = tmp_path / "site_plan.dxf"
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_text("SITE PLAN TITLE", dxfattribs={"layer": "TITLE"})
    doc.saveas(dxf_path)

    extracted = DwgExtractor().extract(dwg, _meta(dwg))
    assert extracted.extra["parse_status"] == "success"
    assert "SITE PLAN TITLE" in extracted.text_content


def test_dwg_extractor_uses_folder_context(tmp_path):
    dwg = tmp_path / "site_plan.dwg"
    dwg.write_bytes(b"AC1032 fake")
    (tmp_path / "grading_notes.pdf").write_text("notes")

    doc = DwgExtractor().extract(dwg, _meta(dwg))
    assert doc.extra["parse_status"] == "partial"
    assert "site_plan.dwg" in doc.text_content
    assert "grading_notes.pdf" in doc.text_content


def test_read_text_head_truncates_large_file(tmp_path):
    path = tmp_path / "big.txt"
    path.write_text("abcdefghij" * 1000, encoding="utf-8")
    text, truncated = read_text_head(path, 100)
    assert truncated
    assert len(text) == 100
