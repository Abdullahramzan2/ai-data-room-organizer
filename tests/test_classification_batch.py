"""Tests for batch classification in the engine."""

from pathlib import Path
from unittest.mock import patch

from dataroom.classification.engine import ClassificationEngine
from dataroom.classification.models import ClassificationConfig, TierResult
from dataroom.ingestion.models import ExtractedDocument, FileMetadata

MINI_TAXONOMY = {
    "categories": [
        {
            "id": "02",
            "folder": "02_Land_Control",
            "description": "Purchase and sale agreements",
            "keywords": ["psa", "purchase and sale"],
        },
        {
            "id": "19",
            "folder": "19_Unclassified_Review_Queue",
            "description": "Review queue",
            "is_review_queue": True,
        },
    ]
}


def _doc(text: str, name: str) -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(f"/tmp/{name}"),
            file_name=name,
            extension=".txt",
            file_size=10,
        ),
        text_content=text,
    )


def test_classify_batch_calls_classify_many_once():
    engine = ClassificationEngine(
        MINI_TAXONOMY,
        ClassificationConfig(),
    )
    docs = [
        _doc("unrelated memo one", "memo1.txt"),
        _doc("unrelated memo two", "memo2.txt"),
    ]
    low = TierResult(
        category_id="02",
        category_folder="02_Land_Control",
        score=0.2,
        method="embedding",
        reason="weak",
    )

    with patch.object(
        engine._embedder,
        "classify_many",
        return_value=[(low, [("02", 0.2)]), (low, [("02", 0.2)])],
    ) as mock_many:
        results = engine.classify_batch(docs)

    mock_many.assert_called_once()
    assert len(mock_many.call_args[0][0]) == 2
    assert len(results) == 2
