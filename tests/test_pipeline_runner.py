"""Tests for UI subprocess pipeline runner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from dataroom.ui.pipeline_runner import (
    PipelineSubprocessError,
    run_pipeline_subprocess,
    run_rerun_subprocess,
)


def test_run_pipeline_subprocess_success(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()
    summary = {"processed": 2, "organized": 2}
    (output_dir / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    with patch(
        "dataroom.ui.pipeline_runner._run_command",
        return_value=(0, "ok"),
    ):
        result = run_pipeline_subprocess(input_dir, output_dir)

    assert result.summary == summary
    assert result.log == "ok"


def test_run_pipeline_subprocess_failure(tmp_path: Path):
    input_dir = tmp_path / "in"
    output_dir = tmp_path / "out"
    input_dir.mkdir()
    output_dir.mkdir()

    with patch(
        "dataroom.ui.pipeline_runner._run_command",
        return_value=(1, "boom"),
    ):
        with pytest.raises(PipelineSubprocessError) as exc_info:
            run_pipeline_subprocess(input_dir, output_dir)

    assert exc_info.value.returncode == 1
    assert "boom" in exc_info.value.log


def test_run_rerun_subprocess_builds_command(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    summary = {"rerun": True, "corrections_applied": 1}
    (output_dir / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")

    with patch(
        "dataroom.ui.pipeline_runner._run_command",
        return_value=(0, ""),
    ) as mock_run:
        result = run_rerun_subprocess(output_dir)

    cmd = mock_run.call_args[0][0]
    assert "rerun" in cmd
    assert str(output_dir) in cmd
    assert result.summary["rerun"] is True
