"""Tests for manifest.xlsx export."""

from openpyxl import load_workbook

from dataroom.export import build_manifest_rows, write_manifest_xlsx


def test_write_manifest_xlsx(tmp_path):
    ingestion_docs = [
        {
            "source_path": "C:/docs/psa.txt",
            "file_name": "psa.txt",
            "extension": ".txt",
            "file_size": 1200,
            "modified_at": "2026-06-01T12:00:00+00:00",
            "file_hash": "abc123",
            "extraction_method": "native",
            "char_count": 100,
        }
    ]
    classification = [
        {
            "source_path": "C:/docs/psa.txt",
            "category_id": "02",
            "category_folder": "02_Land_Control_and_PSA",
            "confidence": "high",
            "score": 0.95,
            "method": "keyword",
            "reason": "Matched PSA",
            "supporting_terms": ["psa"],
            "entities": [],
            "needs_review": False,
            "api_used": False,
        }
    ]

    rows = build_manifest_rows(ingestion_docs, classification, tmp_path / "out")
    xlsx_path = tmp_path / "manifest.xlsx"
    write_manifest_xlsx(xlsx_path, rows)

    wb = load_workbook(xlsx_path)
    ws = wb["Manifest"]
    assert ws.cell(1, 1).value == "file_name"
    assert ws.cell(2, 1).value == "psa.txt"
    assert ws.cell(2, 25).value == "1200"
    assert ws.cell(2, 26).value == "2026-06-01T12:00:00+00:00"
    assert ws.cell(2, 27).value == "abc123"
    assert ws.freeze_panes == "A2"
    assert ws.auto_filter.ref == "A1:AA2"
