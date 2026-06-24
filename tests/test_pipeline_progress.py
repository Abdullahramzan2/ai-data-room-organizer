"""Tests for pipeline run progress snapshots."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dataroom.pipeline.progress import RunProgressTracker, load_run_progress
from dataroom.pipeline import run_pipeline


def test_run_pipeline_writes_progress(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    (input_dir / "PSA_agreement.txt").write_text(
        "purchase and sale agreement PSA escrow closing conditions",
        encoding="utf-8",
    )
    output_dir = tmp_path / "out"

    summary = run_pipeline(input_dir, output_dir, no_ocr=True)

    progress_path = output_dir / "run_progress.json"
    assert progress_path.is_file()
    progress = load_run_progress(progress_path)
    assert progress is not None
    assert progress["status"] == "complete"
    assert progress["total_files"] == 1
    assert progress["classified_count"] == 1
    assert len(progress["files"]) == 1
    assert progress["files"][0]["status"] == "done"
    assert summary["processed"] == 1


def test_progress_tracker_atomic_flush(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    tracker.register_files([tmp_path / "in" / "a.txt"])
    tracker.file_ingesting(tmp_path / "in" / "a.txt", 1, 1)
    tracker.file_ingested(tmp_path / "in" / "a.txt")
    tracker.file_classified(
        tmp_path / "in" / "a.txt",
        category_folder="01_Project_Overview",
        confidence="high",
        needs_review=False,
    )
    tracker.complete({"processed": 1, "review_queue_count": 0, "duplicate_pair_count": 0})

    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["phase"] == "complete"
    assert loaded["files"][0]["category_folder"] == "01_Project_Overview"


def test_run_pipeline_progress_on_failure(tmp_path: Path):
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    with patch("dataroom.pipeline.run.run_ingestion", side_effect=RuntimeError("boom")):
        try:
            run_pipeline(input_dir, output_dir, no_ocr=True)
        except RuntimeError:
            pass

    progress = load_run_progress(output_dir / "run_progress.json")
    assert progress is not None
    assert progress["status"] == "failed"
    assert "boom" in str(progress.get("error", ""))
