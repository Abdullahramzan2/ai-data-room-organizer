"""Destination file naming for organized output."""

from __future__ import annotations

import re
from pathlib import Path


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
) -> str:
    """Return destination file name (preserve original by default)."""
    if not rename:
        return source_path.name

    date_part = date_prefix or "unknown-date"
    category_short = _safe_token(category_folder.split("_", 1)[-1])
    original = source_path.name
    return f"{date_part}__{category_short}__{original}"
