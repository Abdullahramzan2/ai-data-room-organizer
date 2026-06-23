"""Tier 2: local sentence embeddings with FAISS similarity search."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from dataroom.classification.models import ClassificationConfig, TaxonomyCategory, TierResult

logger = logging.getLogger(__name__)


class EmbeddingClassifier:
    """Embed taxonomy categories and rank documents by cosine similarity."""

    def __init__(
        self,
        categories: list[TaxonomyCategory],
        config: ClassificationConfig,
        cache_dir: Path | None = None,
    ):
        self.categories = categories
        self.config = config
        self.cache_dir = cache_dir
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._category_ids: list[str] = []

    def _category_text(self, category: TaxonomyCategory) -> str:
        keywords = " ".join(category.keywords[:20])
        return f"{category.folder}. {category.description} {keywords}".strip()

    def _load_model(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.config.embedding_model)

    def _taxonomy_fingerprint(self) -> str:
        payload = "|".join(f"{c.id}:{self._category_text(c)}" for c in self.categories)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _cache_paths(self) -> tuple[Path, Path] | None:
        if not self.cache_dir:
            return None
        fp = self._taxonomy_fingerprint()
        base = self.cache_dir / "taxonomy_embeddings" / fp
        return base.with_suffix(".index"), base.with_suffix(".ids")

    def _build_index(self) -> None:
        self._load_model()
        assert self._model is not None
        texts = [self._category_text(c) for c in self.categories]
        embeddings = self._model.encode(texts, normalize_embeddings=True)
        vectors = np.asarray(embeddings, dtype=np.float32)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        self._index = index
        self._category_ids = [c.id for c in self.categories]

    def _try_load_cache(self) -> bool:
        paths = self._cache_paths()
        if not paths:
            return False
        index_path, ids_path = paths
        if not index_path.is_file() or not ids_path.is_file():
            return False
        try:
            self._index = faiss.read_index(str(index_path))
            self._category_ids = ids_path.read_text(encoding="utf-8").strip().split("\n")
            return len(self._category_ids) == self._index.ntotal
        except Exception as exc:
            logger.debug("Could not load embedding cache: %s", exc)
            return False

    def _save_cache(self) -> None:
        paths = self._cache_paths()
        if not paths or self._index is None:
            return
        index_path, ids_path = paths
        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(index_path))
        ids_path.write_text("\n".join(self._category_ids), encoding="utf-8")

    def ensure_ready(self) -> None:
        if self._index is not None:
            return
        if not self._try_load_cache():
            self._build_index()
            self._save_cache()

    def classify(
        self,
        file_name: str,
        text: str,
        *,
        top_k: int = 3,
    ) -> tuple[TierResult | None, list[tuple[str, float]]]:
        results = self.classify_many([(file_name, text)], top_k=top_k)
        return results[0]

    def classify_many(
        self,
        items: list[tuple[str, str]],
        *,
        top_k: int = 3,
    ) -> list[tuple[TierResult | None, list[tuple[str, float]]]]:
        """Embed and rank multiple documents in one model.encode() call."""
        if not items:
            return []

        self.ensure_ready()
        assert self._index is not None

        doc_texts: list[str] = []
        empty_indices: set[int] = set()
        for idx, (file_name, text) in enumerate(items):
            excerpt = text[: self.config.excerpt_chars]
            doc_text = f"{file_name}\n{excerpt}".strip()
            if not doc_text:
                empty_indices.add(idx)
                doc_texts.append("")
            else:
                doc_texts.append(doc_text)

        self._load_model()
        assert self._model is not None

        encode_indices = [i for i in range(len(items)) if i not in empty_indices]
        vectors_by_index: dict[int, np.ndarray] = {}
        if encode_indices:
            texts_to_encode = [doc_texts[i] for i in encode_indices]
            encoded = self._model.encode(
                texts_to_encode,
                normalize_embeddings=True,
                batch_size=32,
            )
            for pos, original_idx in enumerate(encode_indices):
                vectors_by_index[original_idx] = np.asarray(encoded[pos], dtype=np.float32)

        results: list[tuple[TierResult | None, list[tuple[str, float]]]] = []
        k = min(top_k, len(self.categories))
        for idx in range(len(items)):
            if idx in empty_indices:
                results.append((None, []))
                continue
            query = np.asarray([vectors_by_index[idx]], dtype=np.float32)
            scores, indices = self._index.search(query, k)
            candidates: list[tuple[str, float]] = []
            for cat_idx, score in zip(indices[0], scores[0], strict=False):
                if cat_idx < 0:
                    continue
                cat_id = self._category_ids[cat_idx]
                candidates.append((cat_id, float(score)))
            if not candidates:
                results.append((None, []))
                continue
            best_id, best_score = candidates[0]
            best_cat = next(c for c in self.categories if c.id == best_id)
            results.append(
                (
                    TierResult(
                        category_id=best_cat.id,
                        category_folder=best_cat.folder,
                        score=best_score,
                        method="embedding",
                        reason=(
                            f"Embedding similarity {best_score:.2f} to "
                            f"category {best_cat.folder}"
                        ),
                    ),
                    candidates,
                )
            )
        return results
