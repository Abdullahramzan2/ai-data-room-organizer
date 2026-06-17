"""Tests for shared LLM response parsing."""

from dataroom.classification.models import TaxonomyCategory
from dataroom.classification.providers.response import (
    parse_classification_data,
    parse_classification_json,
)

CATEGORIES = [
    TaxonomyCategory(id="02", folder="02_Land_Control", description="PSA", keywords=["psa"]),
    TaxonomyCategory(id="19", folder="19_Review", description="Review", keywords=[]),
]


def test_parse_classification_json_valid():
    raw = (
        '{"category_id": "02", "confidence": "high", '
        '"reason": "PSA match", "supporting_terms": ["psa"]}'
    )
    result = parse_classification_json(
        raw,
        CATEGORIES,
        method="openai",
        default_reason="default",
    )
    assert result is not None
    assert result.category_id == "02"
    assert result.category_folder == "02_Land_Control"
    assert result.score == 0.9
    assert result.method == "openai"
    assert result.supporting_terms == ["psa"]
    assert result.reason == "PSA match"


def test_parse_classification_json_invalid_category():
    raw = '{"category_id": "99", "confidence": "high"}'
    assert parse_classification_json(raw, CATEGORIES, method="test", default_reason="x") is None


def test_parse_classification_json_malformed():
    assert parse_classification_json("not json", CATEGORIES, method="test", default_reason="x") is None
    assert parse_classification_json("[]", CATEGORIES, method="test", default_reason="x") is None


def test_parse_classification_data_uses_default_reason():
    result = parse_classification_data(
        {"category_id": "19", "confidence": "low"},
        CATEGORIES,
        method="ollama",
        default_reason="Classified via Ollama",
    )
    assert result is not None
    assert result.reason == "Classified via Ollama"
    assert result.score == 0.3
