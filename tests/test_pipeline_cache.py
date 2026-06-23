"""Tests for pipeline cache persistence."""

import json
from pathlib import Path

from dataroom.pipeline.cache import (
    build_classification_cache_payload,
    build_ingestion_cache_payload,
    load_classification_cache,
    load_ingestion_cache,
    write_classification_cache,
    write_ingestion_cache,
)


def test_ingestion_cache_round_trip(tmp_path: Path):
    docs = [{"source_path": "/a/x.txt", "file_name": "x.txt", "file_hash": "abc"}]
    payload = build_ingestion_cache_payload(
        tmp_path / "in",
        docs,
        skipped_files=[tmp_path / "skip.bin"],
        failed_files=[(tmp_path / "bad.pdf", "parse error")],
    )
    cache_path = tmp_path / "ingestion_cache.json"
    write_ingestion_cache(cache_path, payload)
    loaded = load_ingestion_cache(cache_path)
    assert loaded["documents"] == docs
    assert loaded["skipped_files"] == [str(tmp_path / "skip.bin")]
    assert loaded["failed_files"][0]["error"] == "parse error"


def test_classification_cache_round_trip(tmp_path: Path):
    results = [{"source_path": "/a/x.txt", "category_id": "02"}]
    payload = build_classification_cache_payload(results)
    cache_path = tmp_path / "classification_cache.json"
    write_classification_cache(cache_path, payload)
    loaded = load_classification_cache(cache_path)
    assert loaded["classified"] == 1
    assert loaded["results"] == results
