from pathlib import Path

from dataroom.classification.engine import default_cache_dir
from dataroom.config import load_app_config, resolve_project_root
from dataroom.ingestion.extractors.legacy_office import resolve_libreoffice_cmd
from dataroom.ocr.tesseract import resolve_poppler_path, resolve_tesseract_cmd
from dataroom.paths import (
    bundled_libreoffice_cmd,
    bundled_poppler_path,
    bundled_tesseract_cmd,
    env_example_path,
    is_bundled,
    resolve_app_root,
    resolve_dev_project_root,
    resolve_env_file,
    resolve_install_root,
    resolve_models_dir,
    resolve_tools_dir,
    user_config_dir,
    user_cache_dir,
)
from dataroom.settings import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def _stage_bundle(tmp_path: Path) -> Path:
    """Minimal bundled install tree for path resolution tests."""
    install = tmp_path / "install"
    app = install / "app"
    tools = install / "tools"
    models = install / "models" / "huggingface"

    (app / "config").mkdir(parents=True)
    (app / "config" / "default.yaml").write_text("ocr:\n  enabled: true\n", encoding="utf-8")
    (app / "taxonomy").mkdir()
    (app / ".env.example").write_text("CLASSIFICATION_MODE=local\n", encoding="utf-8")

    tess_dir = tools / "tesseract"
    tess_dir.mkdir(parents=True)
    (tess_dir / "tesseract.exe").write_text("stub", encoding="utf-8")

    pop_dir = tools / "poppler" / "Library" / "bin"
    pop_dir.mkdir(parents=True)
    (pop_dir / "pdftoppm.exe").write_text("stub", encoding="utf-8")

    lo_dir = tools / "libreoffice" / "program"
    lo_dir.mkdir(parents=True)
    (lo_dir / "soffice.exe").write_text("stub", encoding="utf-8")

    models.mkdir(parents=True)
    (models / "config.json").write_text("{}", encoding="utf-8")

    return install


def test_dev_mode_uses_repo_root(monkeypatch):
    monkeypatch.delenv("DATAROOM_HOME", raising=False)
    root = resolve_project_root()
    dev = resolve_dev_project_root()
    assert root == dev
    assert (root / "config" / "default.yaml").is_file()
    assert is_bundled() is False
    assert resolve_install_root() is None


def test_bundled_mode_uses_app_subdirectory(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    assert is_bundled() is True
    assert resolve_install_root() == install.resolve()
    assert resolve_app_root() == (install / "app").resolve()
    assert resolve_project_root() == (install / "app").resolve()
    assert load_app_config()["ocr"]["enabled"] is True


def test_bundled_tools_and_models(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    tools = resolve_tools_dir()
    assert tools is not None
    assert bundled_tesseract_cmd() == str(tools / "tesseract" / "tesseract.exe")
    assert bundled_poppler_path() == str(tools / "poppler" / "Library" / "bin")
    assert bundled_libreoffice_cmd() == str(tools / "libreoffice" / "program" / "soffice.exe")
    assert resolve_models_dir() == (install / "models" / "huggingface").resolve()


def test_bundled_tool_resolvers_prefer_bundle(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    assert resolve_tesseract_cmd(None) == bundled_tesseract_cmd()
    assert resolve_poppler_path(None) == bundled_poppler_path()
    assert resolve_libreoffice_cmd(None) == bundled_libreoffice_cmd()


def test_bundled_user_config_dir(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    config_dir = user_config_dir()
    assert config_dir == tmp_path / "appdata" / "DataRoomOrganizer"
    assert resolve_env_file() == config_dir / ".env"
    assert env_example_path() == install / "app" / ".env.example"


def test_bundled_user_cache_dir(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))

    cache_dir = user_cache_dir()
    assert cache_dir == tmp_path / "appdata" / "DataRoomOrganizer" / "cache"
    assert cache_dir.is_dir()

    config = load_app_config()
    assert default_cache_dir(config) == cache_dir


def test_dev_cache_dir_under_project_output(monkeypatch, tmp_path):
    monkeypatch.delenv("DATAROOM_HOME", raising=False)
    config = load_app_config()
    cache_dir = default_cache_dir(config)
    assert cache_dir == resolve_project_root() / "output" / ".cache"
    assert cache_dir.is_dir()


def test_bundled_settings_load_env_from_appdata(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    appdata = tmp_path / "appdata"
    config_dir = appdata / "DataRoomOrganizer"
    config_dir.mkdir(parents=True)
    (config_dir / ".env").write_text("CLASSIFICATION_MODE=local\n", encoding="utf-8")

    monkeypatch.setenv("DATAROOM_HOME", str(install))
    monkeypatch.setenv("APPDATA", str(appdata))
    _clear_settings_cache()

    settings = get_settings()
    assert settings.classification_mode == "local"


def test_explicit_configured_path_still_wins(monkeypatch, tmp_path):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    custom = tmp_path / "custom-tesseract.exe"
    custom.write_text("stub", encoding="utf-8")
    assert resolve_tesseract_cmd(str(custom)) == str(custom)

    custom_pop = tmp_path / "custom-poppler"
    custom_pop.mkdir()
    (custom_pop / "pdftoppm.exe").write_text("stub", encoding="utf-8")
    assert resolve_poppler_path(str(custom_pop)) == str(custom_pop)

    custom_lo = tmp_path / "custom-soffice.exe"
    custom_lo.write_text("stub", encoding="utf-8")
    assert resolve_libreoffice_cmd(str(custom_lo)) == str(custom_lo)
