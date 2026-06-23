"""Exact duplicate detection via file hash groups."""

from __future__ import annotations

from collections import defaultdict

from dataroom.duplicates.models import DuplicatePair, IngestionRecord


def find_exact_duplicates(records: list[IngestionRecord]) -> list[DuplicatePair]:
    """Group files by hash; emit pairs for groups with more than one file."""
    by_hash: dict[str, list[IngestionRecord]] = defaultdict(list)
    for record in records:
        if not record.file_hash:
            continue
        by_hash[record.file_hash].append(record)

    pairs: list[DuplicatePair] = []
    group_index = 1
    for file_hash, group in sorted(by_hash.items(), key=lambda item: item[0]):
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda r: r.source_path)
        canonical = group[0]
        group_id = f"exact-{group_index:04d}"
        group_index += 1
        for other in group[1:]:
            pairs.append(
                DuplicatePair(
                    group_id=group_id,
                    duplicate_type="exact",
                    file_a_path=canonical.source_path,
                    file_b_path=other.source_path,
                    file_a_hash=file_hash,
                    file_b_hash=file_hash,
                    similarity_score=1.0,
                    recommended_action="likely_duplicate",
                )
            )
    return pairs
