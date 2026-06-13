"""Tests for reasoning provider selection."""

from unittest.mock import MagicMock, patch

from dataroom.classification.providers.factory import create_reasoning_provider
from dataroom.classification.providers.local_provider import LocalReasoningProvider
from dataroom.classification.providers.ollama_provider import OllamaReasoningProvider
from dataroom.classification.providers.openai_provider import OpenAIReasoningProvider
from dataroom.settings import Settings


def test_create_local_provider():
    p = create_reasoning_provider("local", Settings(classification_mode="local"))
    assert isinstance(p, LocalReasoningProvider)
    assert p.provider_id == "local"
    assert not p.is_external


def test_create_openai_provider():
    p = create_reasoning_provider(
        "openai",
        Settings(classification_mode="hybrid", openai_api_key="sk-test"),
    )
    assert isinstance(p, OpenAIReasoningProvider)
    assert p.is_external


def test_create_ollama_provider():
    p = create_reasoning_provider("ollama", Settings(classification_mode="hybrid"))
    assert isinstance(p, OllamaReasoningProvider)
    assert not p.is_external


def test_auto_prefers_openai_when_key_set():
    p = create_reasoning_provider(
        "auto",
        Settings(classification_mode="hybrid", openai_api_key="sk-test"),
    )
    assert isinstance(p, OpenAIReasoningProvider)


def test_auto_falls_back_to_ollama_without_key():
    with patch.object(OllamaReasoningProvider, "is_available", return_value=True):
        p = create_reasoning_provider(
            "auto",
            Settings(classification_mode="hybrid", openai_api_key=None),
        )
    assert isinstance(p, OllamaReasoningProvider)


def test_ollama_classify_graceful_when_unavailable():
    provider = OllamaReasoningProvider(Settings())
    with patch.object(provider, "is_available", return_value=False):
        assert provider.classify("f.pdf", ".pdf", "text", [], [], MagicMock()) is None
