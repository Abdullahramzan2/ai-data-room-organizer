"""Launch the Streamlit UI."""

from __future__ import annotations

import sys
from pathlib import Path

from dataroom.ui.launch_config import streamlit_argv


def main() -> None:
    try:
        import streamlit.web.cli as stcli
    except ImportError as exc:
        raise SystemExit(
            'UI dependencies missing. Install with: pip install -e ".[ui]"'
        ) from exc

    app_path = Path(__file__).resolve().parent / "app.py"
    sys.argv = streamlit_argv(app_path)
    stcli.main()


if __name__ == "__main__":
    main()
