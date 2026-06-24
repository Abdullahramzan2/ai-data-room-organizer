"""Index duplicate pairs by file path for manifest enrichment."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dataroom.duplicates.models import DuplicatePair

_STATUS_PRIORITY = {
    "none": 0,
    "near_duplicate": 1,
    "exact_duplicate": 2,
}


@dataclass(frozen=True)
class DuplicateFileInfo:
    duplicate_status: str
    duplicate_partner_path: str
    duplicate_type: str
    similarity_score: str


def _normalize_path(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except OSError:
        return str(Path(path))


def _status_for_type(duplicate_type: str) -> str:
    if duplicate_type == "exact":
        return "exact_duplicate"
    if duplicate_type == "near":
        return "near_duplicate"
    return duplicate_type or "unknown"


def build_duplicate_lookup(pairs: list[DuplicatePair]) -> dict[str, DuplicateFileInfo]:
    """Map each file path to its strongest duplicate status and partner path(s)."""
    lookup: dict[str, DuplicateFileInfo] = {}

    for pair in pairs:
        status = _status_for_type(pair.duplicate_type)
        score = str(pair.similarity_score)
        for path, partner in (
            (pair.file_a_path, pair.file_b_path),
            (pair.file_b_path, pair.file_a_path),
        ):
            key = _normalize_path(path)
            partner_key = _normalize_path(partner)
            existing = lookup.get(key)
            if existing is None:
                lookup[key] = DuplicateFileInfo(
                    duplicate_status=status,
                    duplicate_partner_path=partner_key,
                    duplicate_type=pair.duplicate_type,
                    similarity_score=score,
                )
                continue

            partners = {p for p in existing.duplicate_partner_path.split("|") if p}
            partners.add(partner_key)
            merged_status = status
            if _STATUS_PRIORITY.get(existing.duplicate_status, 0) > _STATUS_PRIORITY.get(status, 0):
                merged_status = existing.duplicate_status

            lookup[key] = DuplicateFileInfo(
                duplicate_status=merged_status,
                duplicate_partner_path="|".join(sorted(partners)),
                duplicate_type=pair.duplicate_type if merged_status == status else existing.duplicate_type,
                similarity_score=score if merged_status == status else existing.similarity_score,
            )

    return lookup


def duplicate_fields_for_path(
    source_path: str,
    lookup: dict[str, DuplicateFileInfo],
) -> dict[str, str]:
    """Return manifest duplicate columns for a file path."""
    info = lookup.get(_normalize_path(source_path))
    if info is None:
        return {
            "duplicate_status": "none",
            "duplicate_partner_path": "",
            "duplicate_type": "",
            "duplicate_similarity": "",
        }
    return {
        "duplicate_status": info.duplicate_status,
        "duplicate_partner_path": info.duplicate_partner_path,
        "duplicate_type": info.duplicate_type,
        "duplicate_similarity": info.similarity_score,
    }
