"""Lightweight entity and term extraction for classification output."""

from __future__ import annotations

import re

_CAPITALIZED_PHRASE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")
_ACRONYM = re.compile(r"\b[A-Z]{2,}\b")


def extract_entities(text: str, *, max_entities: int = 10) -> list[str]:
    """Extract simple capitalized phrases and acronyms from text."""
    found: list[str] = []
    seen: set[str] = set()

    for pattern in (_CAPITALIZED_PHRASE, _ACRONYM):
        for match in pattern.finditer(text):
            value = match.group(1) if match.lastindex else match.group(0)
            key = value.lower()
            if key in seen or len(value) < 3:
                continue
            seen.add(key)
            found.append(value)
            if len(found) >= max_entities:
                return found
    return found
