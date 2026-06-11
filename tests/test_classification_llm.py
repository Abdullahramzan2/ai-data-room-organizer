from unittest.mock import MagicMock

from dataroom.classification.llm import classify_with_llm
from dataroom.classification.models import ClassificationConfig, TaxonomyCategory
from dataroom.settings import Settings

CATEGORIES = [
    TaxonomyCategory(id="02", folder="02_Land_Control", description="PSA", keywords=["psa"]),
]


def test_llm_skips_without_api_key():
    result = classify_with_llm(
        "PSA.pdf",
        ".pdf",
        "purchase and sale agreement",
        CATEGORIES,
        CATEGORIES,
        ClassificationConfig(),
        Settings(classification_mode="hybrid", openai_api_key=None),
    )
    assert result is None


def test_llm_parses_mock_response():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"category_id": "02", "confidence": "high", "reason": "PSA match", "supporting_terms": ["psa"]}'
                )
            )
        ]
    )
    result = classify_with_llm(
        "PSA.pdf",
        ".pdf",
        "purchase and sale agreement",
        CATEGORIES,
        CATEGORIES,
        ClassificationConfig(),
        Settings(classification_mode="hybrid", openai_api_key="test-key"),
        client=mock_client,
    )
    assert result is not None
    assert result.category_id == "02"
    assert result.method == "openai"
    assert result.score == 0.9
