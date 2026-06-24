"""Tests for classification_log.csv and processing_log.json exports."""

import csv
import json
from pathlib import Path

from dataroom.export.classification_log import (
    CLASSIFICATION_LOG_COLUMNS,
    build_classification_log_rows,
    build_processing_log,
    write_classification_log_csv,
    write_processing_log,
)
from dataroom.pipeline.outputs import export_pipeline_outputs, finalize_run_exports


def _manifest_row(**overrides) -> dict[str, str]:
    base = {
        "file_name": "report.pdf",
        "original_path": "C:/in/report.pdf",
        "output_path": "C:/out/05_Env/report.pdf",
        "category_folder": "05_Environmental",
        "confidence": "high",
        "score": "0.91",
        "classification_method": "embedding",
        "reasoning_provider": "local",
        "api_used": "false",
        "needs_review": "false",
        "duplicate_status": "none",
        "extraction_method": "native",
        "organize_status": "copied",
    }
    base.update(overrides)
    return base


def test_build_classification_log_rows_matches_manifest():
    rows = build_classification_log_rows(
        [_manifest_row()],
        timestamp="2026-06-11T12:00:00+00:00",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["timestamp"] == "2026-06-11T12:00:00+00:00"
    assert row["method"] == "embedding"
    assert row["duplicate_status"] == "none"
    assert list(row.keys()) == CLASSIFICATION_LOG_COLUMNS


def test_write_classification_log_csv(tmp_path: Path):
    path = tmp_path / "classification_log.csv"
    write_classification_log_csv(path, build_classification_log_rows([_manifest_row()]))
    with path.open(encoding="utf-8") as fh:
        loaded = list(csv.DictReader(fh))
    assert len(loaded) == 1
    assert loaded[0]["file_name"] == "report.pdf"


def test_build_processing_log_includes_counts_and_timings():
    summary = {
        "input_dir": "C:/in",
        "output_dir": "C:/out",
        "processed": 3,
        "organized": 3,
        "review_queue_count": 1,
        "duplicate_pair_count": 2,
        "timings": {"total_seconds": 12.5},
        "manifest": "C:/out/manifest.csv",
        "classification_log": "C:/out/classification_log.csv",
    }
    payload = build_processing_log(
        summary=summary,
        run_context={
            "started_at": "2026-06-11T11:00:00+00:00",
            "finished_at": "2026-06-11T11:00:12+00:00",
            "ocr_enabled": True,
            "recursive": True,
            "rename": False,
            "taxonomy_name": "real_estate_development",
            "taxonomy_version": "1.0",
        },
    )
    assert payload["counts"]["processed"] == 3
    assert payload["counts"]["duplicate_pairs"] == 2
    assert payload["ocr_enabled"] is True
    assert payload["timings"]["total_seconds"] == 12.5


def test_export_pipeline_writes_classification_log(tmp_path: Path):
    source = tmp_path / "doc.txt"
    source.write_text("purchase agreement", encoding="utf-8")
    output_dir = tmp_path / "out"
    ingestion_docs = [
        {
            "source_path": str(source),
            "file_name": source.name,
            "extraction_method": "native",
            "char_count": 20,
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

    summary = export_pipeline_outputs(
        output_dir=output_dir,
        config={"output": {}},
        ingestion_docs=ingestion_docs,
        classification_results=classification,
        organized=[],
        duplicate_pairs=[],
        skipped_files=[],
        failed_files=[],
        rename=False,
        persist_classification_cache=False,
        run_context={"started_at": "2026-06-11T12:00:00+00:00"},
    )

    log_path = Path(summary["classification_log"])
    assert log_path.is_file()
    with log_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["file_name"] == "doc.txt"


def test_finalize_run_exports_writes_processing_log_to_admin(tmp_path: Path):
    output_dir = tmp_path / "out"
    admin_dir = output_dir / "00_Admin_and_Index"
    admin_dir.mkdir(parents=True)
    manifest = admin_dir / "manifest.csv"
    manifest.write_text("file_name\na.txt\n", encoding="utf-8")
    classification_log = admin_dir / "classification_log.csv"
    classification_log.write_text("file_name\na.txt\n", encoding="utf-8")
    (output_dir / "run_summary.json").write_text("{}", encoding="utf-8")

    summary = {
        "output_dir": str(output_dir),
        "processed": 1,
        "manifest": str(manifest),
        "manifest_xlsx": str(admin_dir / "manifest.xlsx"),
        "review_queue": str(admin_dir / "review_queue.csv"),
        "duplicate_report": str(admin_dir / "duplicate_report.csv"),
        "errors_report": str(admin_dir / "errors_report.csv"),
        "index_html": str(admin_dir / "index.html"),
        "classification_log": str(classification_log),
        "source_auth_matrix": str(admin_dir / "source_authentication_matrix.csv"),
    }
    for name in ("manifest.xlsx", "review_queue.csv", "duplicate_report.csv", "errors_report.csv", "index.html"):
        (admin_dir / name).write_text("x", encoding="utf-8")

    config = {
        "output": {
            "admin_folder": "00_Admin_and_Index",
            "processing_log_file": "processing_log.json",
        }
    }
    result = finalize_run_exports(
        output_dir,
        config,
        summary,
        run_context={"started_at": "2026-06-11T12:00:00+00:00"},
    )

    assert (admin_dir / "processing_log.json").is_file()
    assert (admin_dir / "run_summary.json").is_file()
    assert result["admin_artifact_count"] >= 5
    assert not (output_dir / "processing_log.json").is_file()

    payload = json.loads((admin_dir / "processing_log.json").read_text(encoding="utf-8"))
    assert payload["counts"]["processed"] == 1
