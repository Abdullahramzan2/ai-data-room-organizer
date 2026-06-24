"""Destination file naming for organized output."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from dataroom.ingestion.metadata_hints import build_rename_metadata


def _safe_token(value: str, max_len: int = 40) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len] or "file"


def build_dest_name(
    source_path: Path,
    category_folder: str,
    *,
    rename: bool = False,
    date_prefix: str | None = None,
    ingestion_doc: dict[str, Any] | None = None,
    classification: dict[str, Any] | None = None,
) -> str:
    """
    Return destination file name (preserve original by default).

    When rename=True, pattern:
    YYYY-MM-DD__CategoryShort__Source__ShortDesc__OriginalFileName.ext
    Source and ShortDesc segments are omitted when not detected.
    """
    if not rename:
        return source_path.name

    metadata = build_rename_metadata(ingestion_doc, classification, source_path)
    date_part = date_prefix or metadata["date"]
    category_short = _safe_token(category_folder.split("_", 1)[-1])
    original = source_path.name

    parts = [date_part, category_short]
    if metadata["source"]:
        parts.append(metadata["source"])
    if metadata["description"]:
        parts.append(metadata["description"])
    parts.append(original)
    return "__".join(parts)
