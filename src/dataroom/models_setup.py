"""Download and cache ML assets used by the organizer."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def embedding_repo_id(model_name: str) -> str:
    """Hugging Face repo id for a sentence-transformers model name."""
    if "/" in model_name:
        return model_name
    return f"sentence-transformers/{model_name}"


def is_embedding_model_cached(model_name: str = DEFAULT_EMBEDDING_MODEL) -> bool:
    """Return True when the model files are already in the local Hugging Face cache."""
    try:
        from huggingface_hub import try_to_load_from_cache

        path = try_to_load_from_cache(embedding_repo_id(model_name), "config.json")
        return path is not None
    except Exception:
        return False


def download_embedding_model(model_name: str = DEFAULT_EMBEDDING_MODEL) -> str:
    """
    Download and cache the sentence-transformers embedding model.

    Returns the model name on success.
    """
    from sentence_transformers import SentenceTransformer

    print(f"Downloading embedding model: {model_name} (~90 MB, one-time)...", file=sys.stderr, flush=True)
    logger.info("Downloading embedding model: %s", model_name)
    SentenceTransformer(model_name)
    print(f"Embedding model ready: {model_name}", file=sys.stderr, flush=True)
    logger.info("Embedding model ready: %s", model_name)
    return model_name


def ensure_embedding_model(
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    *,
    quiet: bool = False,
) -> str:
    """Download the embedding model only when it is not already cached."""
    if is_embedding_model_cached(model_name):
        return model_name
    if not quiet:
        print(
            "Embedding model not cached yet; downloading now "
            "(or run 'dataroom download-models' after install).",
            file=sys.stderr,
            flush=True,
        )
    return download_embedding_model(model_name)


def download_all_models() -> list[str]:
    """Download all models required for a default pipeline run."""
    return [ensure_embedding_model()]


def download_all_models_cli() -> None:
    """Console entry point for ``dataroom-download-models``."""
    models = download_all_models()
    for name in models:
        print(f"Ready: {name}")
