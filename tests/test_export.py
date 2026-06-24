from pathlib import Path

from dataroom.export import build_manifest_rows, write_manifest_xlsx, write_review_queue
from dataroom.export.manifest import MANIFEST_COLUMNS
from dataroom.export.review_queue import read_review_queue
from dataroom.export.xlsx_io import read_table_xlsx


def test_manifest_and_review_queue(tmp_path: Path):
    ingestion_docs = [
        {
            "source_path": "C:/docs/psa.txt",
            "file_name": "psa.txt",
            "extraction_method": "native",
            "char_count": 100,
        }
    ]
    classification = [
        {
            "source_path": "C:/docs/psa.txt",
            "category_id": "19",
            "category_folder": "19_Unclassified_Review_Queue",
            "confidence": "low",
            "score": 0.2,
            "method": "embedding",
            "reason": "weak match",
            "supporting_terms": ["term"],
            "entities": ["Acme Corp"],
            "needs_review": True,
            "review_reason": "Low confidence",
            "api_used": False,
        }
    ]

    rows = build_manifest_rows(ingestion_docs, classification, tmp_path / "out")
    manifest_path = tmp_path / "manifest.xlsx"
    review_path = tmp_path / "review_queue.xlsx"
    write_manifest_xlsx(manifest_path, rows)
    write_review_queue(review_path, rows)

    manifest = read_table_xlsx(manifest_path, MANIFEST_COLUMNS)
    review = read_review_queue(review_path)

    assert len(manifest) == 1
    assert manifest[0]["file_name"] == "psa.txt"
    assert manifest[0]["needs_review"] == "true"
    assert manifest[0]["supporting_terms"] == "term"
    assert manifest[0]["file_type_handler"] == "standard"
    assert "classification_basis" in manifest[0]
    assert len(review) == 1
    assert review[0]["assigned_folder"] == "19_Unclassified_Review_Queue"
