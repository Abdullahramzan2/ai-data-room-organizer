import csv
from pathlib import Path

from dataroom.export import build_manifest_rows, write_manifest_csv, write_review_queue_csv


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
    manifest_path = tmp_path / "manifest.csv"
    review_path = tmp_path / "review_queue.csv"
    write_manifest_csv(manifest_path, rows)
    write_review_queue_csv(review_path, rows)

    with manifest_path.open(encoding="utf-8") as fh:
        manifest = list(csv.DictReader(fh))
    with review_path.open(encoding="utf-8") as fh:
        review = list(csv.DictReader(fh))

    assert len(manifest) == 1
    assert manifest[0]["file_name"] == "psa.txt"
    assert manifest[0]["needs_review"] == "true"
    assert manifest[0]["supporting_terms"] == "term"
    assert len(review) == 1
    assert review[0]["assigned_folder"] == "19_Unclassified_Review_Queue"
