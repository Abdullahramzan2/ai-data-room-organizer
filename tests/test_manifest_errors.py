"""Tests for errors_report and manifest organize columns."""

from pathlib import Path

from dataroom.export import (
    build_ingestion_error_rows,
    build_manifest_rows,
    build_organize_error_rows,
)
from dataroom.organizer.models import OrganizeResult


def test_ingestion_error_rows():
    rows = build_ingestion_error_rows(
        [Path("/data/skip.bin")],
        [(Path("/data/fail.pdf"), "parse error")],
    )
    assert len(rows) == 2
    assert rows[0]["stage"] == "ingestion_skipped"
    assert rows[1]["stage"] == "ingestion_failed"
    assert rows[1]["reason"] == "parse error"


def test_manifest_includes_organize_failure(tmp_path: Path):
    source = tmp_path / "missing.pdf"
    ingestion_docs = [
        {
            "source_path": str(source),
            "file_name": "missing.pdf",
            "extraction_method": "native",
            "char_count": 0,
        }
    ]
    classification = [
        {
            "source_path": str(source),
            "category_id": "19",
            "category_folder": "19_Unclassified_Review_Queue",
            "confidence": "low",
            "score": 0.2,
            "method": "embedding",
            "reason": "weak",
            "supporting_terms": [],
            "entities": [],
            "needs_review": True,
            "review_reason": "Low confidence",
            "api_used": False,
        }
    ]
    organize = [
        OrganizeResult(
            source_path=source,
            dest_path=None,
            category_folder="19_Unclassified_Review_Queue",
            success=False,
            error="Source file not found",
        )
    ]
    rows = build_manifest_rows(
        ingestion_docs,
        classification,
        tmp_path / "out",
        organize_results=organize,
    )
    assert rows[0]["organize_status"] == "failed"
    assert rows[0]["organize_error"] == "Source file not found"
    assert rows[0]["output_path"] == ""


def test_write_errors_report_csv(tmp_path: Path):
    from dataroom.export.errors import ERROR_REPORT_COLUMNS, write_errors_report
    from dataroom.export.xlsx_io import read_table_xlsx

    rows = build_organize_error_rows(
        [
            OrganizeResult(
                source_path=Path("/x/a.pdf"),
                dest_path=None,
                category_folder="19_Unclassified_Review_Queue",
                success=False,
                error="disk full",
            )
        ]
    )
    path = tmp_path / "errors_report.xlsx"
    write_errors_report(path, rows)
    data = read_table_xlsx(path, ERROR_REPORT_COLUMNS)
    assert data[0]["stage"] == "organize_failed"
    assert data[0]["reason"] == "disk full"
