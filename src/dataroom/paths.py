"""Install and application path resolution (dev repo vs bundled installer)."""

from __future__ import annotations

import os
from pathlib import Path


def is_protected_path(path: Path) -> bool:
    """True for locations normal users cannot write (e.g. Program Files)."""
    lowered = str(path.resolve()).lower()
    return "program files" in lowered or "program files (x86)" in lowered


def _infer_bundled_install_root() -> Path | None:
    """Detect install root from module location when ``DATAROOM_HOME`` is unset."""
    module = Path(__file__).resolve()
    for parent in module.parents:
        if parent.name != "app":
            continue
        if not (parent / "config").is_dir():
            continue
        install = parent.parent
        if (install / "python").is_dir() or (install / "launcher").is_dir():
            return install.resolve()
    return None


def resolve_install_root() -> Path | None:
    """Return installer root from env or from the on-disk bundled layout."""
    home = os.environ.get("DATAROOM_HOME", "").strip()
    if home:
        path = Path(home)
        if path.is_dir():
            return path.resolve()
    return _infer_bundled_install_root()


def is_bundled() -> bool:
    """True when running from a bundled install directory."""
    return resolve_install_root() is not None


def uses_user_writable_storage() -> bool:
    """True when config/cache/output must live outside the install folder."""
    return is_bundled() or is_protected_path(resolve_app_root())


def _appdata_config_dir() -> Path:
    appdata = os.environ.get("APPDATA", "").strip()
    if appdata:
        return Path(appdata) / "DataRoomOrganizer"
    return Path.home() / "DataRoomOrganizer"


def resolve_dev_project_root() -> Path:
    """Return repository root in development (parent of ``src/``)."""
    return Path(__file__).resolve().parents[2]


def resolve_app_root() -> Path:
    """Return directory containing ``config/``, ``taxonomy/``, and app assets."""
    install = resolve_install_root()
    if install is not None:
        app = install / "app"
        if app.is_dir():
            return app.resolve()
        return install.resolve()
    return resolve_dev_project_root()


def resolve_project_root() -> Path:
    """Alias for :func:`resolve_app_root` (backward-compatible with dev layout)."""
    return resolve_app_root()


def resolve_tools_dir() -> Path | None:
    """Return ``{install_root}/tools`` when present in a bundled install."""
    install = resolve_install_root()
    if install is None:
        return None
    tools = install / "tools"
    return tools.resolve() if tools.is_dir() else None


def resolve_models_dir() -> Path | None:
    """Return Hugging Face cache directory inside a bundled install, if present."""
    install = resolve_install_root()
    if install is None:
        return None
    hf = install / "models" / "huggingface"
    if hf.is_dir():
        return hf.resolve()
    models = install / "models"
    return models.resolve() if models.is_dir() else None


def user_config_dir() -> Path:
    """Writable config directory (``%APPDATA%\\DataRoomOrganizer`` when bundled)."""
    if uses_user_writable_storage():
        return _appdata_config_dir()
    return resolve_dev_project_root()


def user_cache_dir() -> Path:
    """Writable cache directory for taxonomy embedding indexes and similar artifacts."""
    path = user_config_dir() / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_env_file() -> Path:
    """Path to the active ``.env`` file for the current install mode."""
    return user_config_dir() / ".env"


def env_example_path() -> Path:
    """Path to ``.env.example`` shipped with the application."""
    return resolve_project_root() / ".env.example"


def bundled_tesseract_cmd() -> str | None:
    """Tesseract binary under ``tools/tesseract`` in a bundled install."""
    tools = resolve_tools_dir()
    if tools is None:
        return None
    for rel in ("tesseract/tesseract.exe", "tesseract.exe"):
        candidate = tools / rel
        if candidate.is_file():
            return str(candidate)
    return None


def bundled_poppler_path() -> str | None:
    """Poppler bin directory under ``tools/poppler`` in a bundled install."""
    tools = resolve_tools_dir()
    if tools is None:
        return None
    for rel in ("poppler/Library/bin", "poppler/bin", "poppler"):
        candidate = tools / rel
        if not candidate.is_dir():
            continue
        if (candidate / "pdftoppm.exe").is_file() or (candidate / "pdftoppm").is_file():
            return str(candidate)
    return None


def default_output_dir() -> Path:
    """Writable default output folder for the active install mode."""
    if uses_user_writable_storage():
        path = Path.home() / "Desktop" / "output"
        path.mkdir(parents=True, exist_ok=True)
        return path
    return resolve_project_root() / "output"


def default_input_dir() -> Path:
    """Default input folder hint for the active install mode."""
    if uses_user_writable_storage():
        sample = Path.home() / "Desktop" / "Sample Data"
        if sample.is_dir():
            return sample
        path = Path.home() / "Desktop" / "input"
        path.mkdir(parents=True, exist_ok=True)
        return path
    return resolve_project_root() / "data"


def bundled_libreoffice_cmd() -> str | None:
    """LibreOffice ``soffice`` under ``tools/libreoffice`` in a bundled install."""
    tools = resolve_tools_dir()
    if tools is None:
        return None
    for rel in ("libreoffice/program/soffice.exe", "libreoffice/soffice.exe"):
        candidate = tools / rel
        if candidate.is_file():
            return str(candidate)
    return None
