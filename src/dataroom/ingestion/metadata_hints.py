"""Extract date, source, and description hints for standardized rename."""

from __future__ import annotations

import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

_DATE_IN_TEXT_RE = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
_HEADER_LINE_RE = re.compile(r"^(From|To|Cc|Bcc|Date|Subject):\s*", re.IGNORECASE)
_CAPITALIZED_PHRASE_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b")


def _email_headers(doc: dict[str, Any]) -> dict[str, Any]:
    extra = doc.get("extra") or {}
    headers = extra.get("email_headers") or {}
    return headers if isinstance(headers, dict) else {}


def parse_date_value(value: str | datetime | None) -> str | None:
    """Normalize assorted date strings to YYYY-MM-DD."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()

    text = str(value).strip()
    if not text:
        return None

    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        prefix = text[:10]
        if _DATE_IN_TEXT_RE.fullmatch(prefix):
            return prefix

    iso_match = _DATE_IN_TEXT_RE.search(text)
    if iso_match:
        return iso_match.group(1)

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        pass

    try:
        return parsedate_to_datetime(text).date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        pass

    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def extract_date_hint(doc: dict[str, Any] | None, source_path: Path) -> str:
    """
    Date token priority: email header date → YYYY-MM-DD in text → modified_at → unknown-date.
    """
    if doc:
        headers = _email_headers(doc)
        email_date = parse_date_value(headers.get("date"))
        if email_date:
            return email_date

        text_sample = str(doc.get("combined_text") or doc.get("text_content") or "")[:2000]
        text_date = parse_date_value(text_sample)
        if text_date:
            return text_date

        modified = parse_date_value(doc.get("modified_at"))
        if modified:
            return modified

    return "unknown-date"


def _sanitize_token(value: str, *, max_len: int) -> str:
    cleaned = re.sub(r"[^\w\-]+", "_", value.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:max_len]


def _email_from_token(from_value: str | None) -> str:
    if not from_value:
        return ""
    text = str(from_value).strip()
    if "<" in text and ">" in text:
        name = text.split("<", 1)[0].strip().strip('"')
        if name:
            return _sanitize_token(name, max_len=30)
        email = text.split("<", 1)[1].split(">", 1)[0].strip()
        local = email.split("@", 1)[0]
        return _sanitize_token(local, max_len=30)
    if "@" in text:
        return _sanitize_token(text.split("@", 1)[0], max_len=30)
    return _sanitize_token(text, max_len=30)


def extract_source_hint(
    doc: dict[str, Any] | None,
    classification: dict[str, Any] | None,
) -> str:
    """Email From, first entity, or first capitalized phrase in text."""
    if doc:
        headers = _email_headers(doc)
        from_token = _email_from_token(headers.get("from"))
        if from_token:
            return from_token

    entities = (classification or {}).get("entities") or []
    if entities:
        token = _sanitize_token(str(entities[0]), max_len=30)
        if token:
            return token

    if doc:
        text = str(doc.get("combined_text") or doc.get("text_content") or "")
        match = _CAPITALIZED_PHRASE_RE.search(text)
        if match:
            return _sanitize_token(match.group(0), max_len=30)

    return ""


def _first_meaningful_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or _HEADER_LINE_RE.match(stripped):
            continue
        if len(stripped) < 4:
            continue
        return stripped
    return ""


def extract_description_hint(doc: dict[str, Any] | None) -> str:
    """Email subject or first meaningful content line."""
    if doc:
        headers = _email_headers(doc)
        subject = headers.get("subject")
        if subject:
            token = _sanitize_token(str(subject), max_len=40)
            if token:
                return token

        text = str(doc.get("combined_text") or doc.get("text_content") or "")
        line = _first_meaningful_line(text)
        if line:
            return _sanitize_token(line, max_len=40)

    return ""


def build_rename_metadata(
    doc: dict[str, Any] | None,
    classification: dict[str, Any] | None,
    source_path: Path,
) -> dict[str, str]:
    """Collect rename tokens used by build_dest_name."""
    return {
        "date": extract_date_hint(doc, source_path),
        "source": extract_source_hint(doc, classification),
        "description": extract_description_hint(doc),
    }
