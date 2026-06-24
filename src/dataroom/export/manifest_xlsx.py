"""Write manifest.xlsx for classified documents."""

from __future__ import annotations

from pathlib import Path

from dataroom.export.manifest import MANIFEST_COLUMNS
from dataroom.export.xlsx_io import write_table_xlsx


def write_manifest_xlsx(path: Path, rows: list[dict[str, str]]) -> None:
    """Write manifest rows to an Excel workbook with filter and frozen header."""
    write_table_xlsx(path, MANIFEST_COLUMNS, rows, sheet_title="Manifest")
