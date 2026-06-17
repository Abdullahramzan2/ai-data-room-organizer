"""Models for organized file output."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class OrganizeResult:
    source_path: Path
    dest_path: Path | None
    category_folder: str
    success: bool = True
    error: str | None = None
