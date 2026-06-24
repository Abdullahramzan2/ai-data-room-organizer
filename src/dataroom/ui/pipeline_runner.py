"""Run dataroom CLI commands in a subprocess (for Streamlit UI)."""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from dataroom.config import load_app_config
from dataroom.pipeline.progress import default_progress_path, load_run_progress
from dataroom.ui.helpers import load_run_summary

ProgressCallback = Callable[[dict], None]


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


def _build_run_cmd(
    input_dir: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
    no_ocr: bool = False,
    no_recursive: bool = False,
) -> list[str]:
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
    return cmd


def _build_rerun_cmd(
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
) -> list[str]:
    cmd = [*_cli_base(), "rerun", str(output_dir)]
    if config_path is not None:
        cmd.extend(["--config", str(config_path)])
    if rename:
        cmd.append("--rename")
    return cmd


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


def _poll_progress(
    process: subprocess.Popen[bytes],
    progress_path: Path,
    *,
    on_progress: ProgressCallback | None,
    poll_interval: float,
) -> None:
    while process.poll() is None:
        if on_progress is not None:
            snapshot = load_run_progress(progress_path)
            if snapshot is not None:
                on_progress(snapshot)
        time.sleep(poll_interval)
    if on_progress is not None:
        snapshot = load_run_progress(progress_path)
        if snapshot is not None:
            on_progress(snapshot)


def _execute_subprocess(
    cmd: list[str],
    output_dir: Path,
    *,
    config_path: Path | None,
    on_progress: ProgressCallback | None = None,
    poll_interval: float = 0.5,
) -> tuple[int, str]:
    if on_progress is None:
        return _run_command(cmd)

    config = load_app_config(config_path)
    progress_path = default_progress_path(output_dir, config)
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    _poll_progress(process, progress_path, on_progress=on_progress, poll_interval=poll_interval)
    stderr = process.stderr.read() if process.stderr is not None else ""
    return process.returncode or 0, stderr.strip()


def run_pipeline_subprocess(
    input_dir: Path,
    output_dir: Path,
    *,
    config_path: Path | None = None,
    rename: bool = False,
    no_ocr: bool = False,
    no_recursive: bool = False,
    on_progress: ProgressCallback | None = None,
    poll_interval: float = 0.5,
) -> SubprocessResult:
    """Run ``dataroom run`` in a child process and return run_summary.json."""
    cmd = _build_run_cmd(
        input_dir,
        output_dir,
        config_path=config_path,
        rename=rename,
        no_ocr=no_ocr,
        no_recursive=no_recursive,
    )
    returncode, log = _execute_subprocess(
        cmd,
        output_dir,
        config_path=config_path,
        on_progress=on_progress,
        poll_interval=poll_interval,
    )
    summary = load_run_summary(output_dir)
    if returncode != 0:
        progress_error = ""
        snap = load_run_progress(default_progress_path(output_dir, load_app_config(config_path)))
        if snap and snap.get("error"):
            progress_error = str(snap["error"])
        message = f"dataroom run failed (exit {returncode})"
        if progress_error:
            message = f"{message}: {progress_error}"
        raise PipelineSubprocessError(message, returncode=returncode, log=log)
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
    on_progress: ProgressCallback | None = None,
    poll_interval: float = 0.5,
) -> SubprocessResult:
    """Run ``dataroom rerun`` in a child process and return run_summary.json."""
    cmd = _build_rerun_cmd(output_dir, config_path=config_path, rename=rename)
    returncode, log = _execute_subprocess(
        cmd,
        output_dir,
        config_path=config_path,
        on_progress=on_progress,
        poll_interval=poll_interval,
    )
    summary = load_run_summary(output_dir)
    if returncode != 0:
        progress_error = ""
        snap = load_run_progress(default_progress_path(output_dir, load_app_config(config_path)))
        if snap and snap.get("error"):
            progress_error = str(snap["error"])
        message = f"dataroom rerun failed (exit {returncode})"
        if progress_error:
            message = f"{message}: {progress_error}"
        raise PipelineSubprocessError(message, returncode=returncode, log=log)
    if summary is None:
        raise PipelineSubprocessError(
            "dataroom rerun finished but run_summary.json was not written",
            returncode=returncode,
            log=log,
        )
    return SubprocessResult(summary=summary, log=log)
