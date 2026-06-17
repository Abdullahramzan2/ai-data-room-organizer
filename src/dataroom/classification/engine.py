"""Classification engine orchestrating keyword, embedding, and reasoning providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.classification.embeddings import EmbeddingClassifier
from dataroom.classification.entities import extract_entities
from dataroom.classification.keyword import classify_by_keywords
from dataroom.classification.models import (
    ClassificationConfig,
    ClassificationResult,
    ConfidenceLevel,
    TaxonomyCategory,
    TierResult,
)
from dataroom.classification.mode import tier3_enabled
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.factory import create_reasoning_provider
from dataroom.classification.taxonomy import (
    category_by_id,
    classifiable_categories,
    parse_categories,
    review_queue_category,
)
from dataroom.config import resolve_project_root
from dataroom.guardrails import GuardrailsConfig, GuardrailsEnforcer
from dataroom.ingestion.models import ExtractedDocument
from dataroom.settings import Settings, get_settings


def load_classification_config(app_config: dict[str, Any]) -> ClassificationConfig:
    raw = app_config.get("classification", {})
    chain = raw.get("auto_provider_chain")
    if chain is None:
        auto_chain = ["enterprise", "openai", "ollama", "local"]
    else:
        auto_chain = [str(item).strip().lower() for item in chain if str(item).strip()]
    return ClassificationConfig(
        excerpt_chars=int(raw.get("excerpt_chars", 4000)),
        high_threshold=float(raw.get("high_threshold", 0.75)),
        medium_threshold=float(raw.get("medium_threshold", 0.50)),
        keyword_weight=float(raw.get("keyword_weight", 0.3)),
        embedding_weight=float(raw.get("embedding_weight", 0.7)),
        embedding_model=str(raw.get("embedding_model", "all-MiniLM-L6-v2")),
        llm_excerpt_chars=int(raw.get("llm_excerpt_chars", 3000)),
        top_candidates=int(raw.get("top_candidates", 3)),
        auto_provider_chain=auto_chain or ["enterprise", "openai", "ollama", "local"],
    )


def _score_to_confidence(score: float, config: ClassificationConfig) -> ConfidenceLevel:
    if score >= config.high_threshold:
        return "high"
    if score >= config.medium_threshold:
        return "medium"
    return "low"


def _combine_local_scores(keyword: TierResult | None, embedding: TierResult | None, config: ClassificationConfig) -> TierResult | None:
    if keyword is None and embedding is None:
        return None
    if keyword is None:
        return embedding
    if embedding is None:
        return keyword

    kw_score = keyword.score
    emb_score = embedding.score
    combined = (config.keyword_weight * kw_score) + (config.embedding_weight * emb_score)

    if keyword.category_id == embedding.category_id:
        return TierResult(
            category_id=keyword.category_id,
            category_folder=keyword.category_folder,
            score=min(1.0, combined),
            method="hybrid_local",
            supporting_terms=sorted(set(keyword.supporting_terms + embedding.supporting_terms)),
            reason=f"Keyword ({kw_score:.2f}) + embedding ({emb_score:.2f})",
        )

    if emb_score >= kw_score:
        return TierResult(
            category_id=embedding.category_id,
            category_folder=embedding.category_folder,
            score=min(1.0, config.embedding_weight * emb_score),
            method="embedding",
            supporting_terms=embedding.supporting_terms,
            reason=f"Embedding outranked keyword match ({emb_score:.2f} vs {kw_score:.2f})",
        )
    return TierResult(
        category_id=keyword.category_id,
        category_folder=keyword.category_folder,
        score=min(1.0, config.keyword_weight * kw_score),
        method="keyword",
        supporting_terms=keyword.supporting_terms,
        reason=f"Keyword outranked embedding match ({kw_score:.2f} vs {emb_score:.2f})",
    )


def _finalize_result(
    source_path: Path,
    tier: TierResult,
    confidence: ConfidenceLevel,
    categories: list[TaxonomyCategory],
    text: str,
    *,
    api_used: bool = False,
    reasoning_provider: str | None = None,
) -> ClassificationResult:
    review_cat = review_queue_category(categories)
    needs_review = confidence in {"medium", "low"}
    review_reason: str | None = None
    category_id = tier.category_id
    category_folder = tier.category_folder

    if confidence == "low":
        category_id = review_cat.id
        category_folder = review_cat.folder
        review_reason = f"Low confidence ({tier.score:.2f}): {tier.reason}"
    elif confidence == "medium":
        review_reason = f"Medium confidence ({tier.score:.2f}): {tier.reason}"

    entities = extract_entities(text)
    basis = f"{tier.method}: {tier.reason}"
    return ClassificationResult(
        source_path=source_path,
        category_id=category_id,
        category_folder=category_folder,
        confidence=confidence,
        score=tier.score,
        method=tier.method,
        reason=tier.reason,
        supporting_terms=tier.supporting_terms,
        entities=entities,
        needs_review=needs_review,
        review_reason=review_reason,
        api_used=api_used,
        classification_basis=basis,
        reasoning_provider=reasoning_provider,
    )


class ClassificationEngine:
    """Classify extracted documents into taxonomy folders."""

    def __init__(
        self,
        taxonomy: dict[str, Any],
        config: ClassificationConfig,
        *,
        settings: Settings | None = None,
        cache_dir: Path | None = None,
        reasoning_provider: ReasoningProvider | None = None,
        guardrails: GuardrailsEnforcer | None = None,
        llm_client: Any | None = None,
    ):
        self.settings = settings or get_settings()
        self.config = config
        self.llm_client = llm_client
        self.categories = parse_categories(taxonomy)
        self._classifiable = classifiable_categories(self.categories)
        self._embedder = EmbeddingClassifier(self._classifiable, config, cache_dir=cache_dir)
        self._provider = reasoning_provider or create_reasoning_provider(
            self.settings.reasoning_provider,
            self.settings,
        )
        self._guardrails = guardrails

    def classify_document(self, document: ExtractedDocument) -> ClassificationResult:
        meta = document.metadata
        text = document.combined_text[: self.config.excerpt_chars]
        source_path = meta.source_path

        keyword_result = classify_by_keywords(
            self._classifiable,
            meta.file_name,
            text,
            self.config,
        )
        if keyword_result and keyword_result.score >= self.config.high_threshold:
            confidence = _score_to_confidence(keyword_result.score, self.config)
            return _finalize_result(
                source_path, keyword_result, confidence, self.categories, text,
                reasoning_provider="local",
            )

        if keyword_result and keyword_result.score >= self.config.medium_threshold:
            confidence = _score_to_confidence(keyword_result.score, self.config)
            return _finalize_result(
                source_path, keyword_result, confidence, self.categories, text,
                reasoning_provider="local",
            )

        embedding_result, candidates = self._embedder.classify(
            meta.file_name,
            text,
            top_k=self.config.top_candidates,
        )
        local_result = _combine_local_scores(keyword_result, embedding_result, self.config)

        if local_result and local_result.score >= self.config.medium_threshold:
            confidence = _score_to_confidence(local_result.score, self.config)
            return _finalize_result(
                source_path, local_result, confidence, self.categories, text,
                reasoning_provider="local",
            )

        # Tier 3 — reasoning provider escalation (guardrails enforced)
        local_score = local_result.score if local_result else (keyword_result.score if keyword_result else None)
        provider = self._provider

        if tier3_enabled(self.settings) and provider.provider_id != "local" and provider.is_available():
            allowed = True
            block_reason = ""
            if self._guardrails is not None:
                allowed, block_reason = self._guardrails.can_escalate(
                    document,
                    provider.provider_id,
                    provider.is_external,
                    local_score,
                )
                if not allowed:
                    self._guardrails.record_blocked(
                        meta.file_name,
                        provider.provider_id,
                        block_reason,
                        local_score,
                    )

            if allowed:
                excerpt = text
                if self._guardrails is not None:
                    excerpt = self._guardrails.prepare_excerpt(text, self.config.llm_excerpt_chars)
                else:
                    excerpt = text[: self.config.llm_excerpt_chars]

                candidate_ids = [cid for cid, _ in candidates]
                if local_result:
                    candidate_ids.insert(0, local_result.category_id)
                seen: set[str] = set()
                llm_candidates: list[TaxonomyCategory] = []
                for cid in candidate_ids:
                    if cid in seen:
                        continue
                    cat = category_by_id(self._classifiable, cid)
                    if cat:
                        llm_candidates.append(cat)
                        seen.add(cid)
                if not llm_candidates:
                    llm_candidates = self._classifiable[: self.config.top_candidates]

                provider_result = provider.classify(
                    meta.file_name,
                    meta.extension,
                    excerpt,
                    llm_candidates,
                    self._classifiable,
                    self.config,
                    client=self.llm_client,
                )

                if self._guardrails is not None:
                    self._guardrails.record_external_call(
                        file_name=meta.file_name,
                        provider_id=provider.provider_id,
                        allowed=True,
                        reason="Escalation call executed",
                        chars_sent=len(excerpt),
                        local_score=local_score,
                    )

                if provider_result:
                    confidence = _score_to_confidence(provider_result.score, self.config)
                    return _finalize_result(
                        source_path,
                        provider_result,
                        confidence,
                        self.categories,
                        text,
                        api_used=provider.is_external,
                        reasoning_provider=provider.provider_id,
                    )

        if local_result:
            tier = local_result
        elif keyword_result:
            tier = keyword_result
        elif embedding_result:
            tier = embedding_result
        else:
            tier = TierResult(
                category_id=review_queue_category(self.categories).id,
                category_folder=review_queue_category(self.categories).folder,
                score=0.0,
                method="fallback",
                reason="No keyword or embedding match",
            )
        return _finalize_result(
            source_path, tier, "low", self.categories, text,
            reasoning_provider="local",
        )

    def classify_batch(self, documents: list[ExtractedDocument]) -> list[ClassificationResult]:
        return [self.classify_document(doc) for doc in documents]


def default_cache_dir(app_config: dict[str, Any]) -> Path:
    root = resolve_project_root()
    rel = app_config.get("paths", {}).get("cache_dir", "output/.cache")
    return root / rel
