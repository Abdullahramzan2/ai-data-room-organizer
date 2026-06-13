"""Tests for KMZ and DWG extractors."""

import zipfile
from pathlib import Path

from dataroom.ingestion.extractors.dwg import DwgExtractor
from dataroom.ingestion.extractors.kmz import KmzExtractor, _parse_kml_content
from dataroom.ingestion.models import FileMetadata


def _meta(path: Path) -> FileMetadata:
    return FileMetadata(
        source_path=path,
        file_name=path.name,
        extension=path.suffix.lower(),
        file_size=path.stat().st_size,
    )


SAMPLE_KML = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Folder><name>Wetland Study</name></Folder>
    <Placemark>
      <name>Site Boundary</name>
      <description>USACE wetland delineation area</description>
      <Point><coordinates>-98.5,29.4,0</coordinates></Point>
    </Placemark>
  </Document>
</kml>"""


def test_parse_kml_extracts_placemarks():
    text, signals, status = _parse_kml_content(SAMPLE_KML)
    assert status == "success"
    assert "Site Boundary" in text
    assert "USACE" in text
    assert any("placemark" in s.lower() for s in signals)


def test_kmz_extractor_parses_zip(tmp_path):
    kmz_path = tmp_path / "wetland_study.kmz"
    with zipfile.ZipFile(kmz_path, "w") as zf:
        zf.writestr("doc.kml", SAMPLE_KML)

    doc = KmzExtractor().extract(kmz_path, _meta(kmz_path))
    assert doc.extra["file_type_handler"] == "kmz_parser"
    assert doc.extra["parse_status"] == "success"
    assert "Site Boundary" in doc.text_content
    assert doc.extra["extracted_geo_signals"]


def test_kmz_extractor_filename_fallback(tmp_path):
    bad_kmz = tmp_path / "broken.kmz"
    bad_kmz.write_bytes(b"not a zip")
    doc = KmzExtractor().extract(bad_kmz, _meta(bad_kmz))
    assert doc.extra["parse_status"] == "failed"
    assert "broken" in doc.text_content.lower()


def test_dwg_extractor_uses_folder_context(tmp_path):
    dwg = tmp_path / "site_plan.dwg"
    dwg.write_bytes(b"fake")
    (tmp_path / "grading_notes.pdf").write_text("notes")
    (tmp_path / "boundary.dxf").write_bytes(b"fake")

    doc = DwgExtractor().extract(dwg, _meta(dwg))
    assert doc.extra["file_type_handler"] == "dwg_handler"
    assert doc.extra["parse_status"] == "partial"
    assert "site_plan.dwg" in doc.text_content
    assert "grading_notes.pdf" in doc.text_content
    signals = doc.extra["extracted_cad_signals"]
    assert any("parent_folder" in s for s in signals)
