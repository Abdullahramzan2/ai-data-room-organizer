"""Classification audit log and run-level processing log exports."""

from __future__ import annotations

import csv
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CLASSIFICATION_LOG_COLUMNS = [
    "timestamp",
    "file_name",
    "original_path",
    "output_path",
    "category_folder",
    "confidence",
    "score",
    "method",
    "reasoning_provider",
    "api_used",
    "needs_review",
    "duplicate_status",
    "extraction_method",
    "organize_status",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_content_fingerprint(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def build_classification_log_rows(
    manifest_rows: list[dict[str, str]],
    *,
    timestamp: str | None = None,
) -> list[dict[str, str]]:
    """Build one audit row per manifest row."""
    stamp = timestamp or utc_now_iso()
    rows: list[dict[str, str]] = []
    for row in manifest_rows:
        rows.append(
            {
                "timestamp": stamp,
                "file_name": row.get("file_name", ""),
                "original_path": row.get("original_path", ""),
                "output_path": row.get("output_path", ""),
                "category_folder": row.get("category_folder", ""),
                "confidence": row.get("confidence", ""),
                "score": row.get("score", ""),
                "method": row.get("classification_method", ""),
                "reasoning_provider": row.get("reasoning_provider", ""),
                "api_used": row.get("api_used", ""),
                "needs_review": row.get("needs_review", ""),
                "duplicate_status": row.get("duplicate_status", "none"),
                "extraction_method": row.get("extraction_method", ""),
                "organize_status": row.get("organize_status", ""),
            }
        )
    return rows


def write_classification_log_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CLASSIFICATION_LOG_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def build_processing_log(
    *,
    summary: dict[str, Any],
    run_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge pipeline summary with optional run context into processing_log.json."""
    ctx = run_context or {}
    finished_at = str(ctx.get("finished_at") or summary.get("finished_at") or utc_now_iso())
    duplicate_count = int(summary.get("duplicate_pair_count") or 0)
    processed = int(summary.get("processed") or 0)

    return {
        "started_at": str(ctx.get("started_at") or summary.get("started_at") or ""),
        "finished_at": finished_at,
        "input_dir": str(summary.get("input_dir") or ctx.get("input_dir") or ""),
        "output_dir": str(summary.get("output_dir") or ""),
        "taxonomy_name": str(ctx.get("taxonomy_name") or ""),
        "taxonomy_version": str(ctx.get("taxonomy_version") or ""),
        "taxonomy_fingerprint": str(ctx.get("taxonomy_fingerprint") or ""),
        "config_fingerprint": str(ctx.get("config_fingerprint") or ""),
        "reasoning_provider": str(
            summary.get("reasoning_provider") or ctx.get("reasoning_provider") or ""
        ),
        "ocr_enabled": bool(ctx.get("ocr_enabled", summary.get("ocr_enabled", False))),
        "rename": bool(ctx.get("rename", summary.get("rename", False))),
        "recursive": bool(ctx.get("recursive", summary.get("recursive", True))),
        "rerun": bool(summary.get("rerun", ctx.get("rerun", False))),
        "counts": {
            "processed": processed,
            "organized": int(summary.get("organized") or 0),
            "skipped": int(summary.get("skipped_count") or 0),
            "ingestion_failed": int(summary.get("ingestion_failed_count") or 0),
            "organize_failed": int(summary.get("organize_failed_count") or 0),
            "review_queue": int(summary.get("review_queue_count") or 0),
            "duplicate_pairs": duplicate_count,
            "api_used": int(summary.get("api_used_count") or 0),
        },
        "timings": summary.get("timings") or ctx.get("timings") or {},
        "artifacts": {
            "manifest": summary.get("manifest", ""),
            "manifest_xlsx": summary.get("manifest_xlsx", ""),
            "review_queue": summary.get("review_queue", ""),
            "duplicate_report": summary.get("duplicate_report", ""),
            "errors_report": summary.get("errors_report", ""),
            "index_html": summary.get("index_html", ""),
            "classification_log": summary.get("classification_log", ""),
            "processing_log": summary.get("processing_log", ""),
            "run_summary": str(
                Path(str(summary.get("output_dir") or ".")) / "run_summary.json"
            ),
            "audit_log": summary.get("audit_log", ""),
        },
    }


def write_processing_log(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
