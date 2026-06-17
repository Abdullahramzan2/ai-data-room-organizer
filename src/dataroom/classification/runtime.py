"""Shared runtime setup for classification (pipeline and CLI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from dataroom.classification.engine import load_classification_config
from dataroom.classification.models import ClassificationConfig
from dataroom.classification.providers.base import ReasoningProvider
from dataroom.classification.providers.factory import create_reasoning_provider
from dataroom.guardrails import GuardrailsEnforcer, load_guardrails_config
from dataroom.settings import Settings, get_settings


def build_classification_runtime(
    config: dict[str, Any],
    *,
    output_dir: Path | None = None,
    settings: Settings | None = None,
) -> tuple[Settings, GuardrailsEnforcer, ReasoningProvider, ClassificationConfig]:
    """Load settings, guardrails, provider, and classification config consistently."""
    settings = settings or get_settings()
    guardrails_config = load_guardrails_config(config)
    guardrails = GuardrailsEnforcer(guardrails_config)
    guardrails._audit_path = guardrails.resolve_audit_path(output_dir)

    classification_cfg = load_classification_config(config)
    class_section = config.get("classification", {}) or {}
    provider_name = class_section.get("reasoning_provider") or settings.reasoning_provider
    provider = create_reasoning_provider(
        provider_name,
        settings,
        auto_chain=classification_cfg.auto_provider_chain,
    )
    return settings, guardrails, provider, classification_cfg
