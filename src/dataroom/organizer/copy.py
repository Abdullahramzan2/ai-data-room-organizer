"""Copy classified files into taxonomy folder tree."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from dataroom.organizer.models import OrganizeResult
from dataroom.organizer.naming import build_dest_name


def create_folder_tree(output_dir: Path, taxonomy: dict[str, Any]) -> None:
    """Create all taxonomy folders under output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for cat in taxonomy.get("categories", []):
        folder = cat.get("folder")
        if folder:
            (output_dir / str(folder)).mkdir(parents=True, exist_ok=True)


def _unique_dest_path(dest_dir: Path, file_name: str) -> Path:
    dest = dest_dir / file_name
    if not dest.exists():
        return dest
    stem = Path(file_name).stem
    suffix = Path(file_name).suffix
    n = 2
    while True:
        candidate = dest_dir / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1


def organize_files(
    classifications: list[dict[str, Any]],
    output_dir: Path,
    taxonomy: dict[str, Any],
    *,
    rename: bool = False,
) -> list[OrganizeResult]:
    """Copy each classified file into its category folder. Originals are never modified."""
    create_folder_tree(output_dir, taxonomy)
    organized: list[OrganizeResult] = []

    for row in classifications:
        source = Path(row["source_path"])
        if not source.is_file():
            continue

        category_folder = str(row["category_folder"])
        dest_name = build_dest_name(source, category_folder, rename=rename)
        dest_dir = output_dir / category_folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = _unique_dest_path(dest_dir, dest_name)

        shutil.copy2(source, dest_path)
        organized.append(
            OrganizeResult(
                source_path=source,
                dest_path=dest_path,
                category_folder=category_folder,
            )
        )

    return organized
