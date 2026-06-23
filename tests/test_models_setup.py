"""Tests for model pre-download helpers."""

from unittest.mock import MagicMock, patch

from dataroom.models_setup import (
    DEFAULT_EMBEDDING_MODEL,
    download_all_models,
    download_embedding_model,
    embedding_repo_id,
    ensure_embedding_model,
    is_embedding_model_cached,
)


def test_embedding_repo_id():
    assert embedding_repo_id("all-MiniLM-L6-v2") == "sentence-transformers/all-MiniLM-L6-v2"
    assert embedding_repo_id("org/custom") == "org/custom"


@patch("huggingface_hub.try_to_load_from_cache", return_value="/cache/config.json")
def test_is_embedding_model_cached_true(mock_try):
    assert is_embedding_model_cached(DEFAULT_EMBEDDING_MODEL) is True
    mock_try.assert_called_once_with("sentence-transformers/all-MiniLM-L6-v2", "config.json")


@patch("huggingface_hub.try_to_load_from_cache", return_value=None)
def test_is_embedding_model_cached_false(mock_try):
    assert is_embedding_model_cached(DEFAULT_EMBEDDING_MODEL) is False


@patch("sentence_transformers.SentenceTransformer")
def test_download_embedding_model(mock_st):
    mock_st.return_value = MagicMock()
    name = download_embedding_model("all-MiniLM-L6-v2")
    assert name == "all-MiniLM-L6-v2"
    mock_st.assert_called_once_with("all-MiniLM-L6-v2")


@patch("dataroom.models_setup.download_embedding_model", return_value="all-MiniLM-L6-v2")
@patch("dataroom.models_setup.is_embedding_model_cached", return_value=False)
def test_ensure_embedding_model_downloads_when_missing(mock_cached, mock_download):
    assert ensure_embedding_model(quiet=True) == "all-MiniLM-L6-v2"
    mock_download.assert_called_once_with("all-MiniLM-L6-v2")


@patch("dataroom.models_setup.download_embedding_model")
@patch("dataroom.models_setup.is_embedding_model_cached", return_value=True)
def test_ensure_embedding_model_skips_when_cached(mock_cached, mock_download):
    assert ensure_embedding_model() == "all-MiniLM-L6-v2"
    mock_download.assert_not_called()


@patch("dataroom.models_setup.ensure_embedding_model", return_value="all-MiniLM-L6-v2")
def test_download_all_models(mock_ensure):
    assert download_all_models() == ["all-MiniLM-L6-v2"]
    mock_ensure.assert_called_once()
