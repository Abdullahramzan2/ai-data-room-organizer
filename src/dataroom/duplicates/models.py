"""Shared models for duplicate detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IngestionRecord:
    source_path: str
    file_name: str
    extension: str
    file_size: int
    file_hash: str
    text: str

    @classmethod
    def from_doc(cls, doc: dict[str, Any]) -> IngestionRecord:
        text = (doc.get("combined_text") or doc.get("text_content") or "").strip()
        if not text and doc.get("ocr_text"):
            text = str(doc.get("ocr_text", "")).strip()
        return cls(
            source_path=str(doc["source_path"]),
            file_name=str(doc.get("file_name", "")),
            extension=str(doc.get("extension", "")).lower(),
            file_size=int(doc.get("file_size") or 0),
            file_hash=str(doc.get("file_hash") or ""),
            text=text,
        )


@dataclass(frozen=True)
class DuplicatePair:
    group_id: str
    duplicate_type: str
    file_a_path: str
    file_b_path: str
    file_a_hash: str
    file_b_hash: str
    similarity_score: float
    recommended_action: str
