"""Discover supported files under an input directory."""

from __future__ import annotations

from pathlib import Path


def normalize_extensions(extensions: list[str]) -> set[str]:
    """Return lowercase extensions, each prefixed with a dot."""
    normalized: set[str] = set()
    for ext in extensions:
        ext = ext.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"
        normalized.add(ext)
    return normalized


def scan_folder(
    input_dir: Path,
    supported_extensions: list[str],
    *,
    recursive: bool = True,
) -> list[Path]:
    """
    Recursively list files with supported extensions under input_dir.

    Hidden files and directories are skipped. Results are sorted for stable runs.
    """
    input_dir = input_dir.resolve()
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")

    allowed = normalize_extensions(supported_extensions)
    paths: list[Path] = []

    iterator = input_dir.rglob("*") if recursive else input_dir.glob("*")
    for path in iterator:
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() in allowed:
            paths.append(path.resolve())

    return sorted(paths)


def build_metadata(path: Path) -> dict:
    """Collect basic filesystem metadata for a file."""
    stat = path.stat()
    created = None
    modified = None
    try:
        modified = datetime_from_timestamp(stat.st_mtime)
        created = datetime_from_timestamp(stat.st_ctime)
    except OSError:
        pass

    return {
        "file_size": stat.st_size,
        "created_at": created,
        "modified_at": modified,
    }


def datetime_from_timestamp(ts: float):
    from datetime import datetime, timezone

    return datetime.fromtimestamp(ts, tz=timezone.utc)
