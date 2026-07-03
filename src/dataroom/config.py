"""Load application and taxonomy configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def resolve_project_root() -> Path:
    """Return app root (dev repo or bundled ``app/`` directory)."""
    from dataroom.paths import resolve_app_root

    return resolve_app_root()


def load_app_config(config_path: Path | None = None) -> dict[str, Any]:
    root = resolve_project_root()
    path = config_path or (root / "config" / "default.yaml")
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")
    return load_yaml(path)


def load_taxonomy(taxonomy_path: Path | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    root = resolve_project_root()
    resolved = taxonomy_path
    if resolved is None:
        if config is None:
            config = load_app_config()
        rel = config.get("paths", {}).get("taxonomy_file", "taxonomy/real_estate_development.yaml")
        resolved = root / rel
    if not resolved.is_file():
        raise FileNotFoundError(f"Taxonomy file not found: {resolved}")
    return load_yaml(resolved)
