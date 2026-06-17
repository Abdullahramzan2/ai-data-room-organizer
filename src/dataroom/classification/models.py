"""Data models for document classification."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

ConfidenceLevel = Literal["high", "medium", "low"]


@dataclass
class TaxonomyCategory:
    id: str
    folder: str
    description: str
    keywords: list[str] = field(default_factory=list)
    exclude_if: list[str] = field(default_factory=list)
    is_review_queue: bool = False


@dataclass
class ClassificationConfig:
    excerpt_chars: int = 4000
    high_threshold: float = 0.75
    medium_threshold: float = 0.50
    keyword_weight: float = 0.3
    embedding_weight: float = 0.7
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_excerpt_chars: int = 3000
    top_candidates: int = 3
    auto_provider_chain: list[str] = field(
        default_factory=lambda: ["enterprise", "openai", "ollama", "local"]
    )


@dataclass
class TierResult:
    category_id: str
    category_folder: str
    score: float
    method: str
    supporting_terms: list[str] = field(default_factory=list)
    reason: str = ""


@dataclass
class ClassificationResult:
    source_path: Path
    category_id: str
    category_folder: str
    confidence: ConfidenceLevel
    score: float
    method: str
    reason: str
    supporting_terms: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    needs_review: bool = False
    review_reason: str | None = None
    api_used: bool = False
    classification_basis: str = ""
    reasoning_provider: str | None = None

    def to_dict(self) -> dict[str, Any]:
        basis = self.classification_basis or f"{self.method}: {self.reason}"
        return {
            "source_path": str(self.source_path),
            "category_id": self.category_id,
            "category_folder": self.category_folder,
            "confidence": self.confidence,
            "score": round(self.score, 4),
            "method": self.method,
            "reason": self.reason,
            "supporting_terms": self.supporting_terms,
            "entities": self.entities,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason,
            "api_used": self.api_used,
            "classification_basis": basis,
            "reasoning_provider": self.reasoning_provider,
        }
