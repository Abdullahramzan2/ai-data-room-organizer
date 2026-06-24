"""Atomic run-progress snapshots for live UI polling."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROGRESS_VERSION = 1


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_progress_path(output_dir: Path, config: dict[str, Any] | None = None) -> Path:
    output_cfg = (config or {}).get("output", {}) or {}
    return output_dir / str(output_cfg.get("progress_file", "run_progress.json"))


def load_run_progress(path: Path) -> dict[str, Any] | None:
    """Read the latest progress snapshot, or None if missing or invalid."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


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
        tracker = cls(
            output_dir=output_dir,
            path=default_progress_path(output_dir, config),
            run_kind=run_kind,
            input_dir=str(input_dir) if input_dir else "",
        )
        tracker.flush()
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
        self.flush()

    def set_phase(self, phase: str, *, current_file: str = "") -> None:
        self.phase = phase
        if current_file:
            self.current_file = current_file
        self.flush()

    def file_ingesting(self, path: Path, index: int, total: int) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "ingesting"
        self.current_file = path.name
        self.phase = "ingesting"
        self.total_files = max(self.total_files, total)
        self.flush()

    def file_ingested(self, path: Path) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "ingested"
        self.ingested_count = sum(1 for f in self.files.values() if f.status in {"ingested", "classifying", "done"})
        self.flush()

    def file_classifying(self, path: Path) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            return
        row.status = "classifying"
        self.current_file = path.name
        self.phase = "classifying"
        self.flush()

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
        self.classified_count = sum(1 for f in self.files.values() if f.status == "done")
        self.review_queue_count = sum(1 for f in self.files.values() if f.needs_review)
        self.flush()

    def file_failed(self, path: Path, error: str) -> None:
        key = str(path.resolve())
        row = self.files.get(key)
        if row is None:
            row = FileProgressRow(file_name=path.name, original_path=key)
            self.files[key] = row
            self._order.append(key)
        row.status = "failed"
        row.error = error
        self.failed_count = sum(1 for f in self.files.values() if f.status == "failed")
        self.flush()

    def set_duplicate_pairs(self, pairs: list[dict[str, str]]) -> None:
        self.duplicate_pairs = list(pairs)
        self.duplicate_pair_count = len(pairs)
        self.flush()

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
            self.duplicate_pair_count = int(summary.get("duplicate_pair_count", self.duplicate_pair_count))
            self.failed_count = int(summary.get("ingestion_failed_count", 0)) + int(
                summary.get("organize_failed_count", 0)
            )
            self.classified_count = int(summary.get("processed", self.classified_count))
            self.ingested_count = int(summary.get("processed", self.ingested_count))
            self.total_files = max(self.total_files, int(summary.get("processed", 0)))
        self.flush()

    def fail(self, message: str) -> None:
        self.status = "failed"
        self.phase = "failed"
        self.error = message
        self.current_file = ""
        self.flush()

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

    def flush(self) -> None:
        payload = json.dumps(self.to_dict(), indent=2)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix="run_progress_",
            suffix=".tmp",
            dir=self.path.parent,
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload)
            os.replace(tmp_path, self.path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise
