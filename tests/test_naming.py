"""Tests for metadata hints and standardized rename naming."""

from datetime import datetime, timezone
from pathlib import Path

from dataroom.ingestion.metadata_hints import (
    build_rename_metadata,
    extract_date_hint,
    extract_description_hint,
    extract_source_hint,
    parse_date_value,
)
from dataroom.organizer.naming import build_dest_name
from dataroom.organizer import organize_files

MINI_TAXONOMY = {
    "categories": [
        {"id": "02", "folder": "02_Land_Control"},
    ]
}


def test_parse_date_value_iso_and_email():
    assert parse_date_value("2024-03-15") == "2024-03-15"
    assert parse_date_value("Wed, 15 Mar 2024 12:00:00 +0000") == "2024-03-15"


def test_extract_date_hint_prefers_email_header():
    doc = {
        "modified_at": "2020-01-01T00:00:00+00:00",
        "combined_text": "Meeting on 2019-05-05",
        "extra": {"email_headers": {"date": "Tue, 18 Jun 2024 09:30:00 -0400"}},
    }
    assert extract_date_hint(doc, Path("thread.eml")) == "2024-06-18"


def test_extract_date_hint_uses_text_then_modified(tmp_path: Path):
    source = tmp_path / "memo.txt"
    source.write_text("Project update dated 2023-11-02", encoding="utf-8")
    doc = {
        "combined_text": "Project update dated 2023-11-02",
        "modified_at": "2020-01-01T00:00:00+00:00",
    }
    assert extract_date_hint(doc, source) == "2023-11-02"


def test_extract_source_and_description_from_email():
    doc = {
        "extra": {
            "email_headers": {
                "from": "Jane Smith <jane.smith@example.com>",
                "subject": "Wetland delineation report",
            }
        },
        "combined_text": "From: Jane Smith\nSubject: Wetland delineation report\n\nSee attached.",
    }
    assert extract_source_hint(doc, None) == "Jane_Smith"
    assert extract_description_hint(doc) == "Wetland_delineation_report"


def test_extract_source_uses_entity_fallback():
    doc = {"combined_text": "generic memo text"}
    cls = {"entities": ["Acme Development LLC"]}
    assert extract_source_hint(doc, cls) == "Acme_Development_LLC"


def test_build_dest_name_full_pattern():
    source = Path("C:/in/report.pdf")
    doc = {
        "extra": {
            "email_headers": {
                "from": "Acme Corp <info@acme.com>",
                "date": "2024-01-15",
                "subject": "BRAC cleanup summary",
            }
        }
    }
    name = build_dest_name(
        source,
        "05_Environmental_RCRA_BRAC_FOSET",
        rename=True,
        ingestion_doc=doc,
        classification={"entities": []},
    )
    assert name == (
        "2024-01-15__Environmental_RCRA_BRAC_FOSET__Acme_Corp__"
        "BRAC_cleanup_summary__report.pdf"
    )


def test_build_dest_name_unknown_date_without_metadata(tmp_path: Path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")
    name = build_dest_name(source, "02_Land_Control", rename=True)
    assert name.startswith("unknown-date__Land_Control__report.pdf")


def test_build_dest_name_respects_modified_at(tmp_path: Path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x")
    modified = datetime(2025, 7, 4, 12, 0, tzinfo=timezone.utc)
    doc = {"modified_at": modified.isoformat(), "combined_text": ""}
    name = build_dest_name(
        source,
        "02_Land_Control",
        rename=True,
        ingestion_doc=doc,
    )
    assert name.startswith("2025-07-04__Land_Control__report.pdf")


def test_organize_files_rename_with_ingestion_metadata(tmp_path: Path):
    source = tmp_path / "thread.eml"
    source.write_text("email body", encoding="utf-8")
    output_dir = tmp_path / "out"
    ingestion_doc = {
        "source_path": str(source),
        "combined_text": "From: Bob Builder\nSubject: Site plan revision",
        "extra": {
            "email_headers": {
                "from": "Bob Builder <bob@builder.com>",
                "date": "2024-02-01",
                "subject": "Site plan revision",
            }
        },
    }
    rows = [{"source_path": str(source), "category_folder": "02_Land_Control", "entities": []}]

    results = organize_files(
        rows,
        output_dir,
        MINI_TAXONOMY,
        rename=True,
        ingestion_by_path={str(source): ingestion_doc},
    )

    dest = results[0].dest_path
    assert dest is not None
    assert "2024-02-01__Land_Control__Bob_Builder__Site_plan_revision__thread.eml" == dest.name
