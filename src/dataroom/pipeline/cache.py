"""Persist and load pipeline caches for rerun workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_ingestion_cache_payload(
    input_dir: Path,
    documents: list[dict[str, Any]],
    *,
    skipped_files: list[Path] | None = None,
    failed_files: list[tuple[Path, str]] | None = None,
) -> dict[str, Any]:
    return {
        "input_dir": str(input_dir),
        "documents": documents,
        "skipped_files": [str(p) for p in (skipped_files or [])],
        "failed_files": [
            {"path": str(path), "error": error} for path, error in (failed_files or [])
        ],
    }


def write_ingestion_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_ingestion_cache(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_classification_cache_payload(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {"classified": len(results), "results": results}


def write_classification_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_classification_cache(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
