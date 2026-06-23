"""Duplicate detection orchestration."""

from __future__ import annotations

from typing import Any

from dataroom.duplicates.config import DuplicateConfig
from dataroom.duplicates.exact import find_exact_duplicates
from dataroom.duplicates.models import DuplicatePair, IngestionRecord
from dataroom.duplicates.near import find_near_duplicates


def detect_duplicates(
    ingestion_docs: list[dict[str, Any]],
    config: DuplicateConfig,
) -> list[DuplicatePair]:
    """Find exact and near-duplicate pairs. Never deletes or moves files."""
    if not config.enabled:
        return []

    records = [IngestionRecord.from_doc(doc) for doc in ingestion_docs]
    exact_pairs = find_exact_duplicates(records)
    near_pairs = find_near_duplicates(records, config, exact_pairs=exact_pairs)
    return exact_pairs + near_pairs
