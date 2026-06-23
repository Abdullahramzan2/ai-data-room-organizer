"""Launch the Streamlit UI."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        import streamlit.web.cli as stcli
    except ImportError as exc:
        raise SystemExit(
            'UI dependencies missing. Install with: pip install -e ".[ui]"'
        ) from exc

    app_path = Path(__file__).resolve().parent / "app.py"
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless",
        "true",
    ]
    stcli.main()


if __name__ == "__main__":
    main()
