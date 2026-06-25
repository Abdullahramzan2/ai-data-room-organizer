"""Atomic run-progress snapshots for live UI polling."""

from __future__ import annotations

import errno
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROGRESS_VERSION = 1
_PROGRESS_WRITE_RETRIES = 12
_PROGRESS_READ_RETRIES = 4
_MIN_FLUSH_INTERVAL_SEC = 0.15


def _is_transient_io_error(exc: BaseException) -> bool:
    if isinstance(exc, PermissionError):
        return True
    if isinstance(exc, OSError):
        if getattr(exc, "winerror", None) in {5, 32, 33}:
            return True
        if exc.errno in {errno.EACCES, errno.EPERM, errno.EBUSY, 13, 16, 32}:
            return True
    return False


def _write_text_with_retries(path: Path, payload: str, *, retries: int) -> None:
    last_error: BaseException | None = None
    for attempt in range(retries):
        try:
            with path.open("w", encoding="utf-8") as fh:
                fh.write(payload)
            return
        except OSError as exc:
            last_error = exc
            if _is_transient_io_error(exc) and attempt < retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise
    if last_error is not None:
        raise last_error


def _atomic_write_text(path: Path, payload: str, *, retries: int = _PROGRESS_WRITE_RETRIES) -> None:
    """Write progress JSON; on Windows use in-place write to avoid replace() lock races with the UI."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if sys.platform == "win32":
        _write_text_with_retries(path, payload, retries=retries)
        return

    last_error: BaseException | None = None
    for attempt in range(retries):
        fd, tmp_name = tempfile.mkstemp(
            prefix="run_progress_",
            suffix=".tmp",
            dir=path.parent,
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, path)
            return
        except Exception as exc:
            last_error = exc
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            if _is_transient_io_error(exc) and attempt < retries - 1:
                time.sleep(0.05 * (attempt + 1))
                continue
            raise

    if last_error is not None:
        raise last_error


def _cleanup_stale_progress_temps(output_dir: Path) -> None:
    for tmp in output_dir.glob("run_progress_*.tmp"):
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_progress_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    output_cfg = (config or {}).get("output", {}) or {}
    return output_dir / str(output_cfg.get("progress_file", "run_progress.json"))


def load_run_progress(path: Path) -> dict[str, Any] | None:
    """Read the latest progress snapshot, or None if missing or invalid."""
    if not path.is_file():
        return None
    for attempt in range(_PROGRESS_READ_RETRIES):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            if attempt < _PROGRESS_READ_RETRIES - 1:
                time.sleep(0.03 * (attempt + 1))
                continue
            return None
        except OSError:
            if attempt < _PROGRESS_READ_RETRIES - 1:
                time.sleep(0.03 * (attempt + 1))
                continue
            return None
        return data if isinstance(data, dict) else None
    return None


def summarize_file_progress(files: list[dict[str, Any]], *, total: int = 0) -> dict[str, int]:
    """Derive live counts from per-file rows (source of truth for the UI)."""
    effective_total = total or len(files)
    ingested = 0
    classified = 0
    failed = 0
    skipped = 0
    for row in files:
        status = str(row.get("status", ""))
        if status in {"ingested", "classifying", "done", "failed", "skipped"}:
            ingested += 1
        if status == "done" and row.get("category_folder"):
            classified += 1
        if status == "failed":
            failed += 1
        if status == "skipped":
            skipped += 1
    terminal = classified + failed + skipped
    classifying = sum(1 for row in files if str(row.get("status", "")) == "classifying")
    ingesting = sum(1 for row in files if str(row.get("status", "")) == "ingesting")
    return {
        "total": effective_total,
        "ingested": ingested,
        "classified": classified,
        "classifying": classifying,
        "ingesting": ingesting,
        "failed": failed,
        "skipped": skipped,
        "terminal": terminal,
    }


@dataclass
class FileProgressRow:
    file_name: str
    original_path: str
    status: str = "pending"
    category_folder: str = ""
    confidence: str = ""
    needs_review: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "original_path": self.original_path,
            "status": self.status,
            "category_folder": self.category_folder,
            "confidence": self.confidence,
            "needs_review": self.needs_review,
            "error": self.error,
        }


@dataclass
class RunProgressTracker:
    """Write atomic JSON snapshots to ``output_dir/run_progress.json``."""

    output_dir: Path
    path: Path
    run_kind: str = "run"
    status: str = "running"
    phase: str = "starting"
    input_dir: str = ""
    total_files: int = 0
    ingested_count: int = 0
    classified_count: int = 0
    review_queue_count: int = 0
    duplicate_pair_count: int = 0
    duplicate_pairs: list[dict[str, str]] = field(default_factory=list)
    failed_count: int = 0
    skipped_count: int = 0
    current_file: str = ""
    error: str | None = None
    files: dict[str, FileProgressRow] = field(default_factory=dict)
    _order: list[str] = field(default_factory=list)
    _last_flush_at: float = field(default=0.0, repr=False)

    @classmethod
    def start(
        cls,
        output_dir: Path,
        *,
        input_dir: Path | None = None,
        config: dict[str, Any] | None = None,
        run_kind: str = "run",
    ) -> RunProgressTracker:
        output_dir.mkdir(parents=True, exist_ok=True)
        _cleanup_stale_progress_temps(output_dir)
        tracker = cls(
            output_dir=output_dir,
            path=default_progress_path(output_dir, config),
            run_kind=run_kind,
            input_dir=str(input_dir) if input_dir else "",
        )
        tracker.flush(force=True)
        return tracker

    def register_files(self, paths: list[Path]) -> None:
        self._order = []
        self.files = {}
        for path in paths:
            key = str(path.resolve())
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        self.total_files = len(paths)
        self.phase = "ready"
        self.flush(force=True)

    def begin_ingestion(self) -> None:
        """Mark every pending file as ingesting when the ingestion phase starts."""
        for row in self.files.values():
            if row.status == "pending":
                row.status = "ingesting"
        self.phase = "ingesting"
        self.flush(force=True)

    def set_phase(self, phase: str, *, current_file: str = "") -> None:
        self.phase = phase
        if current_file:
            self.current_file = current_file
        self.flush(force=True)

    def file_ingesting(self, path: Path, index: int, total: int) -> None:
        """Mark the active file as ingesting (other rows keep their current status)."""
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        if row.status in {"pending", "ingested"}:
            row.status = "ingesting"
        self.current_file = path.name
        self.phase = "ingesting"
        self.total_files = max(self.total_files, total)
        self.flush(force=True)

    def _sync_counts_from_files(self) -> None:
        self.ingested_count = sum(
            1
            for row in self.files.values()
            if row.status in {"ingested", "classifying", "done", "failed", "skipped"}
        )
        self.classified_count = sum(
            1
            for row in self.files.values()
            if row.status == "done" and bool(row.category_folder)
        )
        self.failed_count = sum(1 for row in self.files.values() if row.status == "failed")
        self.skipped_count = sum(1 for row in self.files.values() if row.status == "skipped")
        self.review_queue_count = sum(1 for row in self.files.values() if row.needs_review)

    def file_ingested(self, path: Path) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "ingested"
        self._sync_counts_from_files()
        self.flush(force=True)

    def file_skipped(self, path: Path) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "skipped"
        self._sync_counts_from_files()
        self.flush(force=True)

    def file_classifying(self, path: Path) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            return
        row.status = "classifying"
        self.current_file = path.name
        self.phase = "classifying"
        self._sync_counts_from_files()
        self.flush(force=True)

    def file_classified(
        self,
        path: Path,
        *,
        category_folder: str,
        confidence: str,
        needs_review: bool,
    ) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "done"
        row.category_folder = category_folder
        row.confidence = confidence
        row.needs_review = needs_review
        self._sync_counts_from_files()
        self.flush(force=True)

    def file_failed(self, path: Path, error: str) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "failed"
        row.error = error
        row.needs_review = True
        self._sync_counts_from_files()
        self.flush(force=True)

    def set_duplicate_pairs(self, pairs: list[dict[str, str]]) -> None:
        self.duplicate_pairs = list(pairs)
        self.duplicate_pair_count = len(pairs)
        self.flush(force=True)

    def set_duplicate_pair_count(self, count: int) -> None:
        self.duplicate_pair_count = count
        self.flush()

    def set_skipped_count(self, count: int) -> None:
        self.skipped_count = count
        self.flush()

    def complete(self, summary: dict[str, Any] | None = None) -> None:
        self.status = "complete"
        self.phase = "complete"
        self.current_file = ""
        if summary:
            self.review_queue_count = int(summary.get("review_queue_count", self.review_queue_count))
            self.duplicate_pair_count = int(
                summary.get("duplicate_pair_count", self.duplicate_pair_count)
            )
        self._sync_counts_from_files()
        self.flush(force=True)

    def fail(self, message: str) -> None:
        self.status = "failed"
        self.phase = "failed"
        self.error = message
        self.current_file = ""
        self.flush(force=True)

    def to_dict(self) -> dict[str, Any]:
        file_rows = [self.files[key].to_dict() for key in self._order if key in self.files]
        return {
            "version": PROGRESS_VERSION,
            "status": self.status,
            "phase": self.phase,
            "run_kind": self.run_kind,
            "input_dir": self.input_dir,
            "output_dir": str(self.output_dir),
            "total_files": self.total_files,
            "ingested_count": self.ingested_count,
            "classified_count": self.classified_count,
            "review_queue_count": self.review_queue_count,
            "duplicate_pair_count": self.duplicate_pair_count,
            "duplicate_pairs": self.duplicate_pairs,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "current_file": self.current_file,
            "error": self.error,
            "updated_at": _utc_now(),
            "files": file_rows,
        }

    def flush(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if not force and self.status == "running":
            if now - self._last_flush_at < _MIN_FLUSH_INTERVAL_SEC:
                return
        self._last_flush_at = now
        payload = json.dumps(self.to_dict(), indent=2)
        _atomic_write_text(self.path, payload)
