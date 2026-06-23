"""Near-duplicate detection via normalized text similarity."""

from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher

from dataroom.duplicates.config import DuplicateConfig
from dataroom.duplicates.models import DuplicatePair, IngestionRecord


def _normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def _size_bucket(file_size: int, bucket_bytes: int) -> int:
    if file_size <= 0:
        return 0
    return file_size // max(bucket_bytes, 1)


def _similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def find_near_duplicates(
    records: list[IngestionRecord],
    config: DuplicateConfig,
    *,
    exact_pairs: list[DuplicatePair] | None = None,
) -> list[DuplicatePair]:
    """Find near-duplicate pairs within extension/size blocks."""
    exact_paths: set[frozenset[str]] = set()
    for pair in exact_pairs or []:
        exact_paths.add(frozenset({pair.file_a_path, pair.file_b_path}))

    eligible = [
        r
        for r in records
        if len(r.text) >= config.min_text_chars_for_near
    ]
    blocks: dict[tuple[str, int], list[IngestionRecord]] = defaultdict(list)
    for record in eligible:
        key = (record.extension, _size_bucket(record.file_size, config.size_bucket_bytes))
        blocks[key].append(record)

    pairs: list[DuplicatePair] = []
    group_index = 1
    threshold = config.near_similarity_threshold

    for block_records in blocks.values():
        if len(block_records) < 2:
            continue
        sorted_records = sorted(block_records, key=lambda r: r.source_path)
        for i, left in enumerate(sorted_records):
            left_text = _normalize_text(left.text[:50_000])
            for right in sorted_records[i + 1 :]:
                if frozenset({left.source_path, right.source_path}) in exact_paths:
                    continue
                score = _similarity(left_text, _normalize_text(right.text[:50_000]))
                if score < threshold:
                    continue
                action = "likely_duplicate" if score >= 0.98 else "review"
                pairs.append(
                    DuplicatePair(
                        group_id=f"near-{group_index:04d}",
                        duplicate_type="near",
                        file_a_path=left.source_path,
                        file_b_path=right.source_path,
                        file_a_hash=left.file_hash,
                        file_b_hash=right.file_hash,
                        similarity_score=round(score, 4),
                        recommended_action=action,
                    )
                )
                group_index += 1
                if len(pairs) >= config.max_near_pairs:
                    return pairs
    return pairs
