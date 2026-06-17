"""Tests for enterprise and OpenAI-compatible reasoning providers."""

from unittest.mock import MagicMock

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory
from dataroom.classification.providers.enterprise_provider import EnterpriseReasoningProvider
from dataroom.classification.providers.factory import create_reasoning_provider
from dataroom.classification.providers.host_utils import is_trusted_local_host
from dataroom.classification.providers.openai_compatible import (
    OpenAICompatibleConfig,
    OpenAICompatibleProvider,
)
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.settings import Settings

CATEGORIES = [
    TaxonomyCategory(id="02", folder="02_Land_Control", description="PSA", keywords=["psa"]),
]


def _enterprise_settings(**overrides) -> Settings:
    base = dict(
        classification_mode="hybrid",
        enterprise_api_key="ent-key",
        enterprise_base_url="https://api.aleph-alpha.com/v1",
        enterprise_model="luminous-base",
        enterprise_timeout=60.0,
        enterprise_extra_headers={"X-Tenant": "test"},
    )
    base.update(overrides)
    return Settings(**base)


def test_enterprise_unavailable_without_config():
    provider = EnterpriseReasoningProvider(Settings(classification_mode="hybrid"))
    assert not provider.is_available()


def test_enterprise_is_external_for_remote_url():
    provider = EnterpriseReasoningProvider(_enterprise_settings())
    assert provider.is_external is True


def test_enterprise_is_not_external_for_localhost_url():
    provider = EnterpriseReasoningProvider(
        _enterprise_settings(enterprise_base_url="http://localhost:8080/v1")
    )
    assert provider.is_external is False


def test_trusted_local_host_helper():
    assert is_trusted_local_host("http://127.0.0.1:11434")
    assert not is_trusted_local_host("https://api.example.com/v1")


def test_enterprise_classify_with_mock_client():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[
            MagicMock(
                message=MagicMock(
                    content='{"category_id": "02", "confidence": "high", "reason": "PSA", "supporting_terms": ["psa"]}'
                )
            )
        ]
    )
    provider = EnterpriseReasoningProvider(_enterprise_settings())
    result = provider.classify(
        "PSA.pdf",
        ".pdf",
        "purchase and sale agreement",
        CATEGORIES,
        CATEGORIES,
        ClassificationConfig(),
        client=mock_client,
    )
    assert result is not None
    assert result.category_id == "02"
    assert result.method == "enterprise"

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "luminous-base"


def test_openai_compatible_builds_client_with_base_url():
    config = OpenAICompatibleConfig(
        provider_id="enterprise",
        api_key="key",
        base_url="https://gateway.example.com/v1",
        model="model-a",
        timeout=30.0,
        extra_headers={"Authorization": "Bearer key"},
    )
    provider = OpenAICompatibleProvider(config)
    assert provider.is_available()
    client = provider._build_client()
    assert str(client.base_url).rstrip("/").endswith("/v1")


def test_create_enterprise_provider():
    p = create_reasoning_provider("enterprise", _enterprise_settings())
    assert isinstance(p, EnterpriseReasoningProvider)
    assert p.provider_id == "enterprise"


def test_auto_prefers_enterprise_when_configured():
    p = create_reasoning_provider(
        "auto",
        _enterprise_settings(openai_api_key="sk-openai"),
    )
    assert isinstance(p, EnterpriseReasoningProvider)


def test_auto_falls_back_to_openai_without_enterprise():
    p = create_reasoning_provider(
        "auto",
        Settings(
            classification_mode="hybrid",
            openai_api_key="sk-test",
            enterprise_api_key=None,
            enterprise_base_url=None,
            enterprise_model="",
        ),
    )
    assert isinstance(p, OpenAIReasoningProvider)
