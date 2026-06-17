"""Tests for classification mode / Tier 3 gating."""

from dataroom.classification.engine import ClassificationEngine
from dataroom.classification.models import ClassificationConfig
from dataroom.classification.providers.factory import create_reasoning_provider
from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.ingestion.models import ExtractedDocument, FileMetadata
from dataroom.settings import Settings

MINI_TAXONOMY = {
    "categories": [
        {
            "id": "19",
            "folder": "19_Unclassified_Review_Queue",
            "description": "Review queue",
            "keywords": [],
            "is_review_queue": True,
        },
        {
            "id": "02",
            "folder": "02_Land_Control",
            "description": "PSA purchase and sale land control",
            "keywords": ["psa", "purchase and sale"],
        },
    ]
}


def test_explicit_openai_respects_local_mode():
    provider = create_reasoning_provider(
        "openai",
        Settings(classification_mode="local", openai_api_key="sk-test"),
    )
    assert isinstance(provider, LocalReasoningProvider)


def test_explicit_enterprise_respects_local_mode():
    provider = create_reasoning_provider(
        "enterprise",
        Settings(
            classification_mode="local",
            enterprise_api_key="key",
            enterprise_base_url="https://api.example.com/v1",
            enterprise_model="model",
        ),
    )
    assert isinstance(provider, LocalReasoningProvider)


def test_engine_skips_tier3_in_local_mode():
    settings = Settings(classification_mode="local", openai_api_key="sk-test")
    provider = OpenAIReasoningProvider(settings)
    engine = ClassificationEngine(
        MINI_TAXONOMY,
        ClassificationConfig(high_threshold=0.99, medium_threshold=0.99),
        settings=settings,
        reasoning_provider=provider,
    )
    doc = ExtractedDocument(
        metadata=FileMetadata(
            source_path=__import__("pathlib").Path("/data/unknown.xyz"),
            file_name="unknown.xyz",
            extension=".xyz",
            file_size=10,
        ),
        text_content="unrelated content without keywords",
    )
    result = engine.classify_document(doc)
    assert result.reasoning_provider == "local"
    assert result.api_used is False
