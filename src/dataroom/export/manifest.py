"""Build manifest rows for classified documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.organizer.models import OrganizeResult
from dataroom.duplicates.models import DuplicatePair
from dataroom.export.duplicate_index import build_duplicate_lookup, duplicate_fields_for_path
from dataroom.export.manifest_fields import build_text_snippet, infer_document_type

MANIFEST_COLUMNS = [
    "file_name",
    "original_path",
    "output_path",
    "category_id",
    "category_folder",
    "confidence",
    "score",
    "classification_method",
    "classification_reason",
    "classification_basis",
    "supporting_terms",
    "entities",
    "needs_review",
    "needs_review_reason",
    "duplicate_status",
    "duplicate_partner_path",
    "duplicate_type",
    "duplicate_similarity",
    "document_type",
    "text_snippet",
    "notes",
    "extraction_method",
    "char_count",
    "file_type_handler",
    "parse_status",
    "extracted_geo_signals",
    "extracted_cad_signals",
    "reasoning_provider",
    "api_used",
    "organize_status",
    "organize_error",
    "file_size",
    "modified_at",
    "file_hash",
]


def _join_list(values: list[str] | None) -> str:
    return "|".join(values or [])


def _extra_field(doc: dict[str, Any], key: str, default: str = "") -> str:
    extra = doc.get("extra") or {}
    val = extra.get(key, default)
    if isinstance(val, list):
        return _join_list(val)
    return str(val) if val is not None else default


def build_manifest_rows(
    ingestion_docs: list[dict[str, Any]],
    classification_results: list[dict[str, Any]],
    output_dir: Path | None = None,
    *,
    rename: bool = False,
    organize_results: list[OrganizeResult] | None = None,
    duplicate_pairs: list[DuplicatePair] | None = None,
) -> list[dict[str, str]]:
    """Merge ingestion + classification (+ optional organize results) into manifest rows."""
    by_path = {row["source_path"]: row for row in classification_results}
    organize_by_path = {
        str(result.source_path): result for result in (organize_results or [])
    }
    duplicate_lookup = build_duplicate_lookup(duplicate_pairs or [])
    rows: list[dict[str, str]] = []

    for doc in ingestion_docs:
        source_path = doc["source_path"]
        cls = by_path.get(source_path)
        if cls is None:
            continue

        source = Path(source_path)
        organize = organize_by_path.get(source_path)
        output_path = ""
        organize_status = "pending"
        organize_error = ""

        if organize is not None:
            if organize.success and organize.dest_path is not None:
                output_path = str(organize.dest_path)
                organize_status = "copied"
            else:
                organize_status = "failed"
                organize_error = organize.error or "Organize failed"
        elif output_dir is not None:
            from dataroom.organizer.naming import build_dest_name

            dest_name = build_dest_name(
                source,
                str(cls["category_folder"]),
                rename=rename,
                ingestion_doc=doc,
                classification=cls,
            )
            output_path = str(output_dir / cls["category_folder"] / dest_name)
            organize_status = "planned"

        handler = _extra_field(doc, "file_type_handler", "standard")
        parse_status = _extra_field(doc, "parse_status", "success" if doc.get("char_count") else "failed")

        rows.append(
            {
                "file_name": doc["file_name"],
                "original_path": source_path,
                "output_path": output_path,
                "category_id": str(cls["category_id"]),
                "category_folder": str(cls["category_folder"]),
                "confidence": str(cls["confidence"]),
                "score": str(cls["score"]),
                "classification_method": str(cls["method"]),
                "classification_reason": str(cls.get("reason", "")),
                "classification_basis": str(cls.get("classification_basis", "")),
                "supporting_terms": _join_list(cls.get("supporting_terms")),
                "entities": _join_list(cls.get("entities")),
                "needs_review": str(bool(cls.get("needs_review", False))).lower(),
                "needs_review_reason": str(cls.get("review_reason") or ""),
                **duplicate_fields_for_path(source_path, duplicate_lookup),
                "document_type": infer_document_type(doc, cls, handler),
                "text_snippet": build_text_snippet(doc),
                "notes": "",
                "extraction_method": str(doc.get("extraction_method", "")),
                "char_count": str(doc.get("char_count", 0)),
                "file_type_handler": handler,
                "parse_status": parse_status,
                "extracted_geo_signals": _extra_field(doc, "extracted_geo_signals"),
                "extracted_cad_signals": _extra_field(doc, "extracted_cad_signals"),
                "reasoning_provider": str(cls.get("reasoning_provider") or ""),
                "api_used": str(bool(cls.get("api_used", False))).lower(),
                "organize_status": organize_status,
                "organize_error": organize_error,
                "file_size": str(doc.get("file_size", "")),
                "modified_at": str(doc.get("modified_at") or ""),
                "file_hash": str(doc.get("file_hash") or ""),
            }
        )

    return rows
