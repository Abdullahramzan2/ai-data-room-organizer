"""Run dataroom CLI commands in a subprocess (for Streamlit UI)."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from dataroom.ui.helpers import load_run_summary


@dataclass(frozen=True)
class SubprocessResult:
    summary: dict
    log: str


class PipelineSubprocessError(RuntimeError):
    """Raised when a dataroom CLI subprocess exits with an error."""

    def __init__(self, message: str, *, returncode: int, log: str):
        super().__init__(message)
        self.returncode = returncode
        self.log = log


def _cli_base() -> list[str]:
    return [sys.executable, "-m", "dataroom.cli"]


def _run_command(cmd: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_parts = []
    if completed.stdout:
        log_parts.append(completed.stdout.rstrip())
    if completed.stderr:
        log_parts.append(completed.stderr.rstrip())
    return completed.returncode, "\n".join(log_parts)


def run_pipeline_subprocess(
    input_dir: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
    no_ocr: bool = False,
    no_recursive: bool = False,
) -> SubprocessResult:
    """Run ``dataroom run`` in a child process and return run_summary.json."""
    cmd = [
        *_cli_base(),
        "run",
        str(input_dir),
        "--output-dir",
        str(output_dir),
    ]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    if rename:
        cmd.append("--rename")
    if no_ocr:
        cmd.append("--no-ocr")
    if no_recursive:
        cmd.append("--no-recursive")

    returncode, log = _run_command(cmd)
    summary = load_run_summary(output_dir)
    if returncode != 0:
        raise PipelineSubprocessError(
            f"dataroom run failed (exit {returncode})",
            returncode=returncode,
            log=log,
        )
    if summary is None:
        raise PipelineSubprocessError(
            "dataroom run finished but run_summary.json was not written",
            returncode=returncode,
            log=log,
        )
    return SubprocessResult(summary=summary, log=log)


def run_rerun_subprocess(
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
) -> SubprocessResult:
    """Run ``dataroom rerun`` in a child process and return run_summary.json."""
    cmd = [
        *_cli_base(),
        "rerun",
        str(output_dir),
    ]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    if rename:
        cmd.append("--rename")

    returncode, log = _run_command(cmd)
    summary = load_run_summary(output_dir)
    if returncode != 0:
        raise PipelineSubprocessError(
            f"dataroom rerun failed (exit {returncode})",
            returncode=returncode,
            log=log,
        )
    if summary is None:
        raise PipelineSubprocessError(
            "dataroom rerun finished but run_summary.json was not written",
            returncode=returncode,
            log=log,
        )
    return SubprocessResult(summary=summary, log=log)
