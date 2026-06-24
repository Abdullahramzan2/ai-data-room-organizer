from pathlib import Path

import json

from dataroom.pipeline import run_pipeline

ADMIN = "00_Admin_and_Index"


def test_run_pipeline(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "PSA_agreement.txt").write_text(
        "purchase and sale agreement PSA escrow closing conditions",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    summary = run_pipeline(input_dir, output_dir, no_ocr=True)

    admin = output_dir / ADMIN
    assert summary["processed"] == 1
    assert summary["organized"] == 1
    assert (admin / "manifest.xlsx").is_file()
    assert (admin / "index.html").is_file()
    assert (admin / "review_queue.xlsx").is_file()
    assert (admin / "errors_report.xlsx").is_file()
    assert (admin / "duplicate_report.xlsx").is_file()
    assert (admin / "classification_log.xlsx").is_file()
    assert (admin / "processing_log.json").is_file()
    assert (admin / "source_authentication_matrix.xlsx").is_file()
    assert (admin / "run_summary.json").is_file()
    assert not (output_dir / "manifest.xlsx").is_file()
    assert (output_dir / "run_summary.json").is_file()
    assert (output_dir / "ingestion_cache.json").is_file()
    assert (output_dir / "classification_cache.json").is_file()
    assert (input_dir / "PSA_agreement.txt").is_file()

    ingestion_cache = json.loads((output_dir / "ingestion_cache.json").read_text(encoding="utf-8"))
    assert len(ingestion_cache["documents"]) == 1
    assert ingestion_cache["documents"][0]["file_hash"]

    classification_cache = json.loads(
        (output_dir / "classification_cache.json").read_text(encoding="utf-8")
    )
    assert classification_cache["classified"] == 1
    assert len(classification_cache["results"]) == 1

    summary = json.loads((output_dir / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["persist_ingestion_cache"] is True
    assert ADMIN in summary["manifest"]
    assert ADMIN in summary["index_html"]
    assert summary["duplicate_pair_count"] == 0
    assert ADMIN in summary["classification_log"]
    assert ADMIN in summary["processing_log"]
    assert ADMIN in summary["source_auth_matrix"]
    assert summary["admin_folder"].endswith(ADMIN)
    assert summary["admin_artifact_count"] > 0
