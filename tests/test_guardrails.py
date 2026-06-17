"""Tests for guardrails enforcement."""

from pathlib import Path

from dataroom.guardrails import GuardrailsConfig, GuardrailsEnforcer
from dataroom.ingestion.models import ExtractedDocument, FileMetadata
from dataroom.settings import Settings


def _doc(ext: str, name: str = "file") -> ExtractedDocument:
    return ExtractedDocument(
        metadata=FileMetadata(
            source_path=Path(f"/data/{name}{ext}"),
            file_name=f"{name}{ext}",
            extension=ext,
            file_size=100,
        ),
        text_content="sample text",
    )


def test_dwg_blocked_from_escalation():
    cfg = GuardrailsConfig(local_only_extensions=[".dwg", ".kmz"])
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".dwg", "site_plan")
    allowed, reason = enforcer.can_escalate(doc, "openai", True, 0.2)
    assert not allowed
    assert "local-only" in reason.lower()


def test_kmz_blocked_from_escalation():
    cfg = GuardrailsConfig()
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".kmz", "wetlands")
    allowed, _ = enforcer.can_escalate(doc, "openai", True, 0.1)
    assert not allowed


def test_external_blocked_when_disabled():
    cfg = GuardrailsConfig(allow_external_api=False)
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".pdf")
    allowed, reason = enforcer.can_escalate(doc, "openai", True, 0.2)
    assert not allowed
    assert "disabled" in reason.lower()


def test_escalation_skipped_when_local_score_high():
    cfg = GuardrailsConfig(escalation_confidence_threshold=0.50)
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".pdf")
    allowed, reason = enforcer.can_escalate(doc, "openai", True, 0.55)
    assert not allowed
    assert "threshold" in reason.lower()


def test_audit_log_written(tmp_path):
    cfg = GuardrailsConfig(audit_log_enabled=True)
    log_path = tmp_path / "audit.jsonl"
    enforcer = GuardrailsEnforcer(cfg, audit_log_path=log_path)
    enforcer._audit_path = log_path
    enforcer.record_blocked("test.pdf", "openai", "blocked for test", 0.2)
    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "external_call_decision" in content
    assert "test.pdf" in content


def test_max_external_chars_truncates():
    cfg = GuardrailsConfig(max_external_chars=100)
    enforcer = GuardrailsEnforcer(cfg)
    excerpt = enforcer.prepare_excerpt("x" * 500, 3000)
    assert len(excerpt) == 100


def test_provider_block_list():
    cfg = GuardrailsConfig(provider_block_list=["openai"])
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".pdf")
    allowed, reason = enforcer.can_escalate(doc, "openai", True, 0.2)
    assert not allowed
    assert "blocked" in reason.lower()


def test_provider_allow_list():
    cfg = GuardrailsConfig(provider_allow_list=["ollama"])
    enforcer = GuardrailsEnforcer(cfg)
    doc = _doc(".pdf")
    allowed, reason = enforcer.can_escalate(doc, "openai", True, 0.2)
    assert not allowed
    assert "allow list" in reason.lower()


def test_remote_ollama_treated_as_external():
    from dataroom.classification.providers.ollama_provider import OllamaReasoningProvider

    provider = OllamaReasoningProvider(
        Settings(ollama_base_url="https://ollama.example.com")
    )
    assert provider.is_external is True
