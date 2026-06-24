"""Guardrails configuration loading."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GuardrailsConfig:
    allow_external_api: bool = True
    max_external_chars: int = 3000
    local_only_extensions: list[str] = field(
        default_factory=lambda: [".dwg", ".dxf", ".kmz", ".kml", ".geojson", ".gpx"]
    )
    local_only_folders: list[str] = field(default_factory=list)
    escalation_confidence_threshold: float = 0.50
    max_api_cost_per_run_usd: float = 2.0
    uncertain_action: str = "needs_review"
    audit_log_enabled: bool = True
    audit_log_file: str = "output/audit_log.jsonl"
    trusted_local_hosts: list[str] = field(
        default_factory=lambda: ["localhost", "127.0.0.1", "::1"]
    )
    provider_allow_list: list[str] = field(default_factory=list)
    provider_block_list: list[str] = field(default_factory=list)


def load_guardrails_config(app_config: dict[str, Any] | None = None) -> GuardrailsConfig:
    """Load guardrails from the guardrails section of config/default.yaml."""
    raw = (app_config or {}).get("guardrails", {}) or {}
    extensions = [
        str(e).lower() if str(e).startswith(".") else f".{str(e).lower()}"
        for e in raw.get("local_only_extensions", [])
    ]
    trusted_hosts = [str(h).lower() for h in raw.get("trusted_local_hosts", [])]
    allow_list = [str(p).lower() for p in raw.get("provider_allow_list", [])]
    block_list = [str(p).lower() for p in raw.get("provider_block_list", [])]
    return GuardrailsConfig(
        allow_external_api=bool(raw.get("allow_external_api", True)),
        max_external_chars=int(raw.get("max_external_chars", 3000)),
        local_only_extensions=extensions
        or [".dwg", ".dxf", ".kmz", ".kml", ".geojson", ".gpx"],
        local_only_folders=[str(f).lower() for f in raw.get("local_only_folders", [])],
        escalation_confidence_threshold=float(raw.get("escalation_confidence_threshold", 0.50)),
        max_api_cost_per_run_usd=float(raw.get("max_api_cost_per_run_usd", 2.0)),
        uncertain_action=str(raw.get("uncertain_action", "needs_review")),
        audit_log_enabled=bool(raw.get("audit_log_enabled", True)),
        audit_log_file=str(raw.get("audit_log_file", "output/audit_log.jsonl")),
        trusted_local_hosts=trusted_hosts or ["localhost", "127.0.0.1", "::1"],
        provider_allow_list=allow_list,
        provider_block_list=block_list,
    )
