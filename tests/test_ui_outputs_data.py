"""Tests for Outputs tab data helpers."""

from __future__ import annotations

import json
from pathlib import Path

from dataroom.export.manifest import MANIFEST_COLUMNS
from dataroom.export.manifest_xlsx import write_manifest_xlsx
from dataroom.ui.helpers import list_output_artifacts
from dataroom.ui.outputs_data import (
    MANIFEST_PREVIEW_COLUMNS,
    list_admin_mirror_files,
    load_manifest_preview_rows,
    load_processing_log,
)


def _write_manifest(path: Path) -> None:
    row = {col: "" for col in MANIFEST_COLUMNS}
    row.update(
        {
            "file_name": "report.pdf",
            "category_folder": "05_Environmental",
            "confidence": "high",
            "duplicate_status": "none",
            "document_type": "pdf",
            "needs_review": "false",
            "text_snippet": "BRAC summary excerpt",
            "output_path": "C:/out/05/report.pdf",
        }
    )
    write_manifest_xlsx(path, [row])


def test_load_manifest_preview_rows(tmp_path: Path):
    manifest = tmp_path / "manifest.xlsx"
    _write_manifest(manifest)
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"manifest": str(manifest)}),
        encoding="utf-8",
    )
    rows = load_manifest_preview_rows(tmp_path)
    assert len(rows) == 1
    assert set(rows[0].keys()) == set(MANIFEST_PREVIEW_COLUMNS)
    assert rows[0]["text_snippet"] == "BRAC summary excerpt"


def test_load_processing_log(tmp_path: Path):
    log_path = tmp_path / "processing_log.json"
    payload = {
        "started_at": "2026-06-11T12:00:00+00:00",
        "counts": {"processed": 2, "review_queue": 1, "duplicate_pairs": 0},
        "ocr_enabled": True,
        "rename": False,
    }
    log_path.write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "run_summary.json").write_text(
        json.dumps({"processing_log": str(log_path)}),
        encoding="utf-8",
    )
    loaded = load_processing_log(tmp_path)
    assert loaded is not None
    assert loaded["counts"]["processed"] == 2


def test_list_admin_mirror_files(tmp_path: Path):
    admin = tmp_path / "00_Admin_and_Index"
    admin.mkdir()
    (admin / "manifest.xlsx").write_text("x", encoding="utf-8")
    (admin / "index.html").write_text("<html></html>", encoding="utf-8")
    files = list_admin_mirror_files(admin)
    assert len(files) == 2
    assert files[0]["file"] == "index.html"


def test_list_output_artifacts_includes_audit_and_logs(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "classification_log.xlsx").write_text("x", encoding="utf-8")
    (output_dir / "processing_log.json").write_text("{}", encoding="utf-8")
    (output_dir / "audit_log.jsonl").write_text("{}", encoding="utf-8")
    (output_dir / "run_summary.json").write_text(
        json.dumps(
            {
                "classification_log": str(output_dir / "classification_log.xlsx"),
                "processing_log": str(output_dir / "processing_log.json"),
                "audit_log": str(output_dir / "audit_log.jsonl"),
                "admin_folder": str(output_dir / "00_Admin_and_Index"),
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "00_Admin_and_Index").mkdir()

    labels = {a["artifact"] for a in list_output_artifacts(output_dir)}
    assert "classification_log.xlsx" in labels
    assert "processing_log.json" in labels
    assert "audit_log.jsonl" in labels
    assert "00_Admin_and_Index/ (mirror)" not in labels
    assert "00_Admin_and_Index/" in labels
