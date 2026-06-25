"""Filename and metadata signals for image-only (scanned) PDFs."""

from __future__ import annotations

import re
from pathlib import Path

_FILENAME_ACRONYMS: dict[str, str] = {
    "ccr": "covenants conditions restrictions",
    "cc&r": "covenants conditions restrictions",
    "reso": "resolution",
    "psa": "purchase and sale agreement",
    "loi": "letter of intent",
    "esa": "environmental site assessment",
    "alta": "alta survey",
    "cc": "covenants conditions",
}


def _expand_token(token: str) -> list[str]:
    lowered = token.lower()
    expanded: list[str] = [token]
    if lowered in _FILENAME_ACRONYMS:
        expanded.append(_FILENAME_ACRONYMS[lowered])
    return expanded


def _filename_tokens(path: Path) -> list[str]:
    stem = path.stem
    raw = re.split(r"[-_\s]+", stem)
    tokens: list[str] = []
    for part in raw:
        part = part.strip()
        if not part:
            continue
        if part.isdigit() and len(part) == 8:
            tokens.append(part)
            continue
        for piece in _expand_token(part):
            if piece and piece not in tokens:
                tokens.append(piece)
    return tokens


def build_scanned_pdf_context(
    path: Path,
    *,
    pdf_metadata: dict[str, str | None] | None = None,
    page_count: int | None = None,
) -> tuple[str, list[str]]:
    """
    Build searchable text from filename and PDF metadata when no native text exists.

    Returns ``(combined_text, signal_list)``.
    """
    signals: list[str] = [f"filename:{path.name}"]
    lines = [f"PDF filename: {path.name}"]

    tokens = _filename_tokens(path)
    if tokens:
        joined = ", ".join(tokens)
        signals.append(f"filename_tokens:{joined}")
        lines.append(f"Filename tokens: {joined}")

    meta = pdf_metadata or {}
    for key in ("title", "author", "subject", "creator", "producer"):
        value = meta.get(key)
        if value and str(value).strip():
            text = str(value).strip()
            signals.append(f"pdf_{key}:{text}")
            lines.append(f"PDF {key}: {text}")

    if page_count is not None:
        signals.append(f"page_count:{page_count}")
        lines.append(f"PDF pages: {page_count}")

    signals.append("document_type:scanned_pdf")
    lines.append("Scanned document: image-only PDF (no native text layer)")

    return "\n".join(lines), signals
