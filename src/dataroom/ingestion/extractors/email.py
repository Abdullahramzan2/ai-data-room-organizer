"""Email file extractors (.msg, .eml)."""

from __future__ import annotations

import email
from email import policy
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


class EmlExtractor(BaseExtractor):
    extensions = {".eml"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        try:
            raw = path.read_bytes()
            message = email.message_from_bytes(raw, policy=policy.default)
            parts = [
                f"From: {message.get('From', '')}",
                f"To: {message.get('To', '')}",
                f"Cc: {message.get('Cc', '')}",
                f"Date: {message.get('Date', '')}",
                f"Subject: {message.get('Subject', '')}",
                "",
                _extract_body(message),
            ]
            doc.text_content = self._truncate("\n".join(parts))
            doc.extra["email_headers"] = {
                "from": message.get("From"),
                "to": message.get("To"),
                "date": message.get("Date"),
                "subject": message.get("Subject"),
            }
        except Exception as exc:
            doc.errors.append(f"EML extraction failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
        return doc


class MsgExtractor(BaseExtractor):
    extensions = {".msg"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        try:
            import extract_msg

            msg = extract_msg.Message(str(path))
            process = getattr(msg, "process", None)
            if callable(process):
                process()
            parts = [
                f"From: {msg.sender or ''}",
                f"To: {msg.to or ''}",
                f"Cc: {msg.cc or ''}",
                f"Date: {msg.date or ''}",
                f"Subject: {msg.subject or ''}",
                "",
                msg.body or "",
            ]
            doc.text_content = self._truncate("\n".join(parts))
            doc.extra["email_headers"] = {
                "from": msg.sender,
                "to": msg.to,
                "date": str(msg.date) if msg.date else None,
                "subject": msg.subject,
            }
            msg.close()
        except ImportError:
            doc.warnings.append("extract-msg not installed; .msg parsing unavailable")
            doc.extraction_method = ExtractionMethod.FAILED
        except Exception as exc:
            doc.errors.append(f"MSG extraction failed: {exc}")
            doc.extraction_method = ExtractionMethod.FAILED
        return doc


def _extract_body(message: EmailMessage) -> str:
    if message.is_multipart():
        chunks: list[str] = []
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    content = _part_content(part)
                    if content:
                        chunks.append(content)
                except Exception:
                    pass
        return "\n".join(chunks)
    try:
        return _part_content(message)
    except Exception:
        return ""


def _part_content(part: Any) -> str:
    get_content = getattr(part, "get_content", None)
    if callable(get_content):
        content = get_content()
        return content if isinstance(content, str) else str(content)
    payload = part.get_payload(decode=True)
    if isinstance(payload, bytes):
        return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
    if isinstance(payload, str):
        return payload
    return ""
