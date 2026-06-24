"""Tests for UI progress helpers."""

from __future__ import annotations

import json
from pathlib import Path

from dataroom.ui.helpers import load_pipeline_progress, progress_path


def test_load_pipeline_progress(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    payload = {"status": "running", "total_files": 3, "classified_count": 1, "files": []}
    path = progress_path(output_dir)
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_pipeline_progress(output_dir)
    assert loaded is not None
    assert loaded["total_files"] == 3
