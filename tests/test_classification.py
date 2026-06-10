from pathlib import Path
from unittest.mock import patch

from dataroom.classification.engine import ClassificationEngine
from dataroom.classification.keyword import classify_by_keywords
from dataroom.classification.models import ClassificationConfig, TierResult
from dataroom.classification.taxonomy import classifiable_categories, parse_categories
from dataroom.ingestion.models import ExtractedDocument, FileMetadata
from dataroom.settings import Settings

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


def _sample_doc(text: str, name: str = "PSA_Amendment.pdf") -> ExtractedDocument:
    path = Path(f"/tmp/{name}")
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=path,
            file_name=name,
            extension=".pdf",
            file_size=100,
        ),
        text_content=text,
    )


def test_keyword_matches_land_control():
    categories = classifiable_categories(parse_categories(MINI_TAXONOMY))
    result = classify_by_keywords(
        categories,
        "PSA_Amendment.pdf",
        "purchase and sale agreement terms",
        ClassificationConfig(),
    )
    assert result is not None
    assert result.category_id == "02"
    assert result.score >= 0.75


def test_engine_high_keyword_match():
    engine = ClassificationEngine(MINI_TAXONOMY, ClassificationConfig())
    doc = _sample_doc("purchase and sale agreement with escrow and closing conditions")

    with patch.object(engine._embedder, "classify") as mock_classify:
        result = engine.classify_document(doc)

    mock_classify.assert_not_called()
    assert result.category_id == "02"
    assert result.confidence == "high"


def test_engine_low_confidence_goes_to_review_queue():
    engine = ClassificationEngine(
        MINI_TAXONOMY,
        ClassificationConfig(),
        settings=Settings(classification_mode="local"),
    )
    doc = _sample_doc("random unrelated memo about lunch plans")

    low_embedding = TierResult(
        category_id="02",
        category_folder="02_Land_Control",
        score=0.2,
        method="embedding",
        reason="weak match",
    )
    with patch.object(engine._embedder, "classify", return_value=(low_embedding, [("02", 0.2)])):
        result = engine.classify_document(doc)

    assert result.category_id == "19"
    assert result.confidence == "low"
    assert result.needs_review is True
