"""Duplicate detection configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DuplicateConfig:
    enabled: bool = True
    hash_algorithm: str = "sha256"
    near_similarity_threshold: float = 0.92
    min_text_chars_for_near: int = 100
    max_near_pairs: int = 50000
    size_bucket_bytes: int = 4096
    flag_for_review: bool = True


def load_duplicate_config(app_config: dict[str, Any]) -> DuplicateConfig:
    raw = app_config.get("duplicates", {})
    return DuplicateConfig(
        enabled=bool(raw.get("enabled", True)),
        hash_algorithm=str(raw.get("hash_algorithm", "sha256")).strip().lower(),
        near_similarity_threshold=float(raw.get("near_similarity_threshold", 0.92)),
        min_text_chars_for_near=int(raw.get("min_text_chars_for_near", 100)),
        max_near_pairs=int(raw.get("max_near_pairs", 50000)),
        size_bucket_bytes=int(raw.get("size_bucket_bytes", 4096)),
        flag_for_review=bool(raw.get("flag_for_review", True)),
    )
