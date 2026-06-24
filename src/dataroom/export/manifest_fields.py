"""Helpers for enriched manifest column values."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SNIPPET_MAX_LEN = 300


def build_text_snippet(doc: dict[str, Any], *, max_len: int = _SNIPPET_MAX_LEN) -> str:
    """First N characters of combined/native/OCR text, normalized for CSV."""
    parts = [
        str(doc.get("combined_text") or "").strip(),
        str(doc.get("text_content") or "").strip(),
        str(doc.get("ocr_text") or "").strip(),
    ]
    text = next((part for part in parts if part), "")
    text = re.sub(r"\s+", " ", text)
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def infer_document_type(doc: dict[str, Any], cls: dict[str, Any], handler: str) -> str:
    """Lightweight document type label from extension, handler, and method."""
    extension = str(doc.get("extension") or Path(str(doc.get("file_name", ""))).suffix).lower()
    method = str(cls.get("method") or "")

    if handler in {"kmz_parser", "kml_parser", "geojson_parser", "gpx_parser"}:
        return f"geographic/{handler.replace('_parser', '')}"
    if handler == "dwg_handler":
        return "cad/dwg"
    if handler == "dxf_parser":
        return "cad/dxf"
    if extension in {".msg", ".eml"}:
        return "email"
    if extension == ".pdf":
        return "pdf/scanned" if doc.get("ocr_applied") else "pdf"
    if extension in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}:
        return "image"
    if extension in {".doc", ".docx"}:
        return "word"
    if extension in {".xls", ".xlsx"}:
        return "spreadsheet"
    if extension in {".ppt", ".pptx"}:
        return "presentation"
    if extension == ".txt":
        return "text"
    if extension:
        return extension.lstrip(".")
    if method:
        return method
    return "unknown"
