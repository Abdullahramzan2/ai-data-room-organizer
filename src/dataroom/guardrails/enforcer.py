"""Guardrails enforcement before external reasoning calls."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dataroom.config import resolve_project_root
from dataroom.guardrails.config import GuardrailsConfig
from dataroom.ingestion.models import ExtractedDocument


class GuardrailsEnforcer:
    """Enforce guardrails before external reasoning calls."""

    # Rough estimate for cost tracking (USD per 1k input tokens)
    _COST_PER_1K_CHARS = 0.00015

    def __init__(self, config: GuardrailsConfig, audit_log_path: Path | None = None):
        self.config = config
        self._audit_path = audit_log_path
        self._run_cost_usd = 0.0

    @property
    def run_cost_usd(self) -> float:
        return self._run_cost_usd

    def resolve_audit_path(self, output_dir: Path | None = None) -> Path | None:
        if not self.config.audit_log_enabled:
            return None
        if output_dir is not None:
            return output_dir / "audit_log.jsonl"
        root = resolve_project_root()
        p = Path(self.config.audit_log_file)
        return p if p.is_absolute() else root / p

    def is_local_only(self, document: ExtractedDocument) -> bool:
        ext = document.metadata.extension.lower()
        if ext in self.config.local_only_extensions:
            return True
        path_lower = str(document.metadata.source_path).lower()
        for fragment in self.config.local_only_folders:
            if fragment and fragment in path_lower:
                return True
        return False

    def should_escalate(self, local_score: float | None) -> bool:
        if local_score is None:
            return True
        return local_score < self.config.escalation_confidence_threshold

    def prepare_excerpt(self, text: str, llm_default_chars: int) -> str:
        limit = min(self.config.max_external_chars, llm_default_chars)
        return text[:limit].strip()

    def can_escalate(
        self,
        document: ExtractedDocument,
        provider_id: str,
        is_external: bool,
        local_score: float | None,
    ) -> tuple[bool, str]:
        if self.is_local_only(document):
            return False, f"File restricted to local-only ({document.metadata.extension})"

        if not self.should_escalate(local_score):
            return False, f"Local score {local_score:.2f} meets escalation threshold"

        if is_external and not self.config.allow_external_api:
            return False, "External API disabled in guardrails config"

        if is_external and self.config.max_api_cost_per_run_usd > 0:
            if self._run_cost_usd >= self.config.max_api_cost_per_run_usd:
                return False, "Max API cost per run exceeded"

        return True, "Escalation permitted by guardrails"

    def record_external_call(
        self,
        *,
        file_name: str,
        provider_id: str,
        allowed: bool,
        reason: str,
        chars_sent: int = 0,
        local_score: float | None = None,
    ) -> None:
        if allowed and chars_sent > 0:
            est = (chars_sent / 1000) * self._COST_PER_1K_CHARS
            self._run_cost_usd += est

        self._write_audit(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event": "external_call_decision",
                "file_name": file_name,
                "provider": provider_id,
                "allowed": allowed,
                "reason": reason,
                "chars_sent": chars_sent if allowed else 0,
                "local_score": local_score,
                "cumulative_cost_usd": round(self._run_cost_usd, 6),
            }
        )

    def record_blocked(self, file_name: str, provider_id: str, reason: str, local_score: float | None = None) -> None:
        self.record_external_call(
            file_name=file_name,
            provider_id=provider_id,
            allowed=False,
            reason=reason,
            local_score=local_score,
        )

    def _write_audit(self, entry: dict[str, Any]) -> None:
        if not self.config.audit_log_enabled:
            return
        path = self._audit_path
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
