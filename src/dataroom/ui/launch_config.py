"""Shared Streamlit launch configuration."""

from __future__ import annotations

from pathlib import Path


def streamlit_argv(app_path: Path, *, port: int = 8501) -> list[str]:
    """CLI argv for `streamlit run` with settings suited to this project."""
    return [
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        # Avoid scanning transformers/sentence-transformers in site-packages (noisy + slow).
        "--server.fileWatcherType",
        "none",
    ]
