from pathlib import Path

import json

from dataroom.pipeline import run_pipeline


def test_run_pipeline(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "PSA_agreement.txt").write_text(
        "purchase and sale agreement PSA escrow closing conditions",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    summary = run_pipeline(input_dir, output_dir, no_ocr=True)

    assert summary["processed"] == 1
    assert summary["organized"] == 1
    assert (output_dir / "manifest.csv").is_file()
    assert (output_dir / "review_queue.csv").is_file()
    assert (output_dir / "errors_report.csv").is_file()
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
    assert summary["ingestion_cache"].endswith("ingestion_cache.json")
    assert summary["classification_cache"].endswith("classification_cache.json")
