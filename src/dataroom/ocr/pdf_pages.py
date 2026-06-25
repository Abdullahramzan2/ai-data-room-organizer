"""PDF page-count helper without rendering pages."""

from __future__ import annotations

from pathlib import Path


def pdf_page_count(path: Path) -> int:
    import fitz

    with fitz.open(path) as pdf:
        return pdf.page_count
