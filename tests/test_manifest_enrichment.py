"""Tests for manifest enrichment columns and duplicate lookup."""

from pathlib import Path

from dataroom.duplicates.models import DuplicatePair
from dataroom.export import build_manifest_rows, write_manifest_xlsx
from dataroom.export.xlsx_io import read_table_xlsx
from dataroom.export.duplicate_index import build_duplicate_lookup, duplicate_fields_for_path
from dataroom.export.manifest import MANIFEST_COLUMNS
from dataroom.export.manifest_fields import build_text_snippet, infer_document_type


def _sample_doc(path: Path, **overrides) -> dict:
    base = {
        "source_path": str(path),
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "extraction_method": "native",
        "char_count": 50,
        "combined_text": "USACE wetland delineation report for Section 404 review.",
        "text_content": "USACE wetland delineation report for Section 404 review.",
    }
    base.update(overrides)
    return base


def _sample_cls(path: Path, **overrides) -> dict:
    base = {
        "source_path": str(path),
        "category_id": "06",
        "category_folder": "06_Wetlands_Streams_USACE",
        "confidence": "high",
        "score": 0.9,
        "method": "embedding",
        "reason": "wetland terms",
        "supporting_terms": ["USACE"],
        "entities": [],
        "needs_review": False,
        "review_reason": None,
        "api_used": False,
    }
    base.update(overrides)
    return base


def test_build_duplicate_lookup_exact_pair(tmp_path):
    file_a = tmp_path / "a.pdf"
    file_b = tmp_path / "b.pdf"
    file_a.write_bytes(b"x")
    file_b.write_bytes(b"x")
    pair = DuplicatePair(
        group_id="g1",
        duplicate_type="exact",
        file_a_path=str(file_a),
        file_b_path=str(file_b),
        file_a_hash="h1",
        file_b_hash="h1",
        similarity_score=1.0,
        recommended_action="likely_duplicate",
    )
    lookup = build_duplicate_lookup([pair])
    fields_a = duplicate_fields_for_path(str(file_a), lookup)
    fields_b = duplicate_fields_for_path(str(file_b), lookup)
    assert fields_a["duplicate_status"] == "exact_duplicate"
    assert fields_b["duplicate_status"] == "exact_duplicate"
    assert Path(fields_a["duplicate_partner_path"]).name == "b.pdf"
    assert Path(fields_b["duplicate_partner_path"]).name == "a.pdf"


def test_build_duplicate_lookup_prefers_exact_over_near(tmp_path):
    target = tmp_path / "doc.pdf"
    target.write_bytes(b"x")
    partner_exact = tmp_path / "exact.pdf"
    partner_near = tmp_path / "near.pdf"
    lookup = build_duplicate_lookup(
        [
            DuplicatePair(
                group_id="g1",
                duplicate_type="near",
                file_a_path=str(target),
                file_b_path=str(partner_near),
                file_a_hash="h1",
                file_b_hash="h2",
                similarity_score=0.93,
                recommended_action="review",
            ),
            DuplicatePair(
                group_id="g2",
                duplicate_type="exact",
                file_a_path=str(target),
                file_b_path=str(partner_exact),
                file_a_hash="h1",
                file_b_hash="h1",
                similarity_score=1.0,
                recommended_action="likely_duplicate",
            ),
        ]
    )
    fields = duplicate_fields_for_path(str(target), lookup)
    assert fields["duplicate_status"] == "exact_duplicate"
    assert partner_exact.name in fields["duplicate_partner_path"]
    assert partner_near.name in fields["duplicate_partner_path"]


def test_build_text_snippet_truncates_and_normalizes():
    doc = {"combined_text": "Line one\n\nLine two   with   spaces"}
    snippet = build_text_snippet(doc, max_len=20)
    assert snippet.endswith("...")
    assert "\n" not in snippet


def test_infer_document_type_for_email_handler():
    doc = {"file_name": "thread.msg", "extension": ".msg"}
    cls = {"method": "keyword"}
    assert infer_document_type(doc, cls, "standard") == "email"


def test_manifest_rows_include_enrichment_columns(tmp_path):
    source = tmp_path / "wetland.pdf"
    source.write_bytes(b"pdf")
    ingestion_docs = [_sample_doc(source, ocr_applied=True)]
    classification = [_sample_cls(source)]
    partner = tmp_path / "wetland_copy.pdf"
    pairs = [
        DuplicatePair(
            group_id="g1",
            duplicate_type="exact",
            file_a_path=str(source),
            file_b_path=str(partner),
            file_a_hash="h1",
            file_b_hash="h1",
            similarity_score=1.0,
            recommended_action="likely_duplicate",
        )
    ]

    rows = build_manifest_rows(
        ingestion_docs,
        classification,
        tmp_path / "out",
        duplicate_pairs=pairs,
    )
    row = rows[0]
    assert row["duplicate_status"] == "exact_duplicate"
    assert row["duplicate_partner_path"].endswith("wetland_copy.pdf")
    assert row["document_type"] == "pdf/scanned"
    assert "USACE" in row["text_snippet"]
    assert row["notes"] == ""

    manifest_path = tmp_path / "manifest.xlsx"
    write_manifest_xlsx(manifest_path, rows)
    loaded = read_table_xlsx(manifest_path, MANIFEST_COLUMNS)
    assert loaded[0]["duplicate_status"] == "exact_duplicate"
    for column in (
        "duplicate_status",
        "duplicate_partner_path",
        "document_type",
        "text_snippet",
        "notes",
    ):
        assert column in MANIFEST_COLUMNS
    assert MANIFEST_COLUMNS.index("duplicate_status") < MANIFEST_COLUMNS.index("extraction_method")
