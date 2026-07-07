"""Tests for pipeline run progress snapshots."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from dataroom.pipeline.progress import RunProgressTracker, load_run_progress


def test_run_pipeline_writes_progress(tmp_path: Path):
    from dataroom.pipeline import run_pipeline

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


def test_file_failed_counts_toward_review_queue(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    bad = tmp_path / "in" / "bad.pdf"
    tracker.register_files([bad])
    tracker.file_failed(bad, "parse error")

    assert tracker.failed_count == 1
    assert tracker.review_queue_count == 1
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["files"][0]["needs_review"] is True
    assert loaded["files"][0]["status"] == "failed"


def test_file_ingested_updates_progress_incrementally(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    first = tmp_path / "in" / "a.txt"
    second = tmp_path / "in" / "b.txt"
    tracker.register_files([first, second])
    tracker.begin_ingestion()
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["files"][0]["status"] == "ingesting"
    assert loaded["files"][1]["status"] == "ingesting"

    tracker.file_ingested(first)
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["ingested_count"] == 1
    assert loaded["classified_count"] == 0
    assert loaded["files"][0]["status"] == "ingested"
    assert loaded["files"][1]["status"] == "ingesting"

    tracker.file_ingested(second)
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["ingested_count"] == 2
    assert loaded["classified_count"] == 0
    assert loaded["files"][1]["status"] == "ingested"


def test_ingested_does_not_count_as_classified(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    path = tmp_path / "in" / "a.txt"
    tracker.register_files([path])
    tracker.begin_ingestion()
    tracker.file_ingested(path)

    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["ingested_count"] == 1
    assert loaded["classified_count"] == 0
    assert loaded["files"][0]["status"] == "ingested"
    assert loaded["files"][0]["category_folder"] == ""


def test_complete_recounts_from_file_rows(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    first = tmp_path / "in" / "a.txt"
    second = tmp_path / "in" / "b.txt"
    tracker.register_files([first, second])
    tracker.begin_ingestion()
    tracker.file_ingested(first)
    tracker.file_ingested(second)
    tracker.file_classified(
        first,
        category_folder="01_Project_Overview",
        confidence="high",
        needs_review=False,
    )

    tracker.complete({"processed": 99, "review_queue_count": 0, "duplicate_pair_count": 0})
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert loaded["classified_count"] == 1
    assert loaded["ingested_count"] == 2


def test_begin_ingestion_marks_all_pending_as_ingesting(tmp_path: Path):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    paths = [tmp_path / "in" / f"f{i}.txt" for i in range(3)]
    tracker.register_files(paths)
    tracker.begin_ingestion()
    loaded = load_run_progress(tracker.path)
    assert loaded is not None
    assert all(row["status"] == "ingesting" for row in loaded["files"])


def test_progress_flush_retries_on_lock(tmp_path: Path, monkeypatch):
    tracker = RunProgressTracker.start(tmp_path / "out", input_dir=tmp_path / "in")
    tracker.register_files([tmp_path / "in" / "a.txt"])
    original_open = Path.open
    calls = {"count": 0}

    def flaky_open(self, *args, **kwargs):
        if self == tracker.path and kwargs.get("mode", args[0] if args else "") in {"w", "w+"}:
            calls["count"] += 1
            if calls["count"] == 1:
                raise PermissionError(13, "Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", flaky_open)
    tracker.flush(force=True)

    assert calls["count"] == 2
    loaded = load_run_progress(tracker.path)
    assert loaded is not None


def test_run_pipeline_progress_on_failure(tmp_path: Path):
    from dataroom.pipeline import run_pipeline

    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"

    with patch("dataroom.pipeline.run.run_ingestion_from_files", side_effect=RuntimeError("boom")):
        try:
            run_pipeline(input_dir, output_dir, no_ocr=True)
        except RuntimeError:
            pass

    progress = load_run_progress(output_dir / "run_progress.json")
    assert progress is not None
    assert progress["status"] == "failed"
    assert "boom" in str(progress.get("error", ""))
