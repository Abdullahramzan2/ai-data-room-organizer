from dataroom.settings import Settings, api_escalation_enabled, get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_api_escalation_disabled_without_key(monkeypatch):
    _clear_settings_cache()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("CLASSIFICATION_MODE", "hybrid")
    assert api_escalation_enabled() is False


def test_api_escalation_enabled_in_hybrid_mode(monkeypatch):
    _clear_settings_cache()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLASSIFICATION_MODE", "hybrid")
    assert api_escalation_enabled() is True


def test_api_escalation_disabled_in_local_mode(monkeypatch):
    _clear_settings_cache()
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("CLASSIFICATION_MODE", "local")
    assert api_escalation_enabled() is False


def test_get_settings_defaults(monkeypatch):
    _clear_settings_cache()
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CLASSIFICATION_MODE", raising=False)
    settings = get_settings()
    assert settings.classification_mode == "hybrid"
    assert settings.openai_api_key is None
    assert settings.openai_model == "gpt-4o-mini"
