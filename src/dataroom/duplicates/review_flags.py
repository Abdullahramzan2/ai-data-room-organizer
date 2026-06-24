"""Flag classification results that appear in duplicate pairs for human review."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.duplicates.models import DuplicatePair
from dataroom.export.duplicate_index import build_duplicate_lookup, duplicate_fields_for_path


def _duplicate_review_message(fields: dict[str, str]) -> str:
    status = fields["duplicate_status"].replace("_", " ")
    partner_path = fields.get("duplicate_partner_path", "")
    partner_label = partner_path
    if partner_path and "|" not in partner_path:
        partner_label = Path(partner_path).name
    elif partner_path:
        partner_label = ", ".join(Path(part).name for part in partner_path.split("|"))

    similarity = fields.get("duplicate_similarity", "")
    message = f"Duplicate: {status}"
    if similarity:
        message += f" (similarity {similarity})"
    if partner_label:
        message += f" with {partner_label}"
    return message


def apply_duplicate_review_flags(
    classification_results: list[dict[str, Any]],
    pairs: list[DuplicatePair],
    *,
    flag_for_review: bool = True,
) -> int:
    """
    Mark files in duplicate pairs for review and append duplicate context to review_reason.

    Returns the number of rows newly flagged for review.
    """
    if not flag_for_review or not pairs:
        return 0

    lookup = build_duplicate_lookup(pairs)
    newly_flagged = 0

    for row in classification_results:
        fields = duplicate_fields_for_path(str(row.get("source_path", "")), lookup)
        if fields["duplicate_status"] == "none":
            continue

        message = _duplicate_review_message(fields)
        if not row.get("needs_review"):
            row["needs_review"] = True
            newly_flagged += 1

        existing = str(row.get("review_reason") or "").strip()
        if message in existing:
            continue
        row["review_reason"] = f"{existing} | {message}" if existing else message

    return newly_flagged
