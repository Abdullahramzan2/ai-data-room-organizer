"""Native folder picker for local Streamlit UI (Windows/desktop)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_PICKER_SCRIPT = """
import sys
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
try:
    root.attributes("-topmost", True)
except tk.TclError:
    pass
kwargs = {"title": sys.argv[1]}
if len(sys.argv) > 2 and sys.argv[2]:
    kwargs["initialdir"] = sys.argv[2]
selected = filedialog.askdirectory(**kwargs)
if selected:
    print(selected)
root.destroy()
"""


def browse_folder(
    initial_dir: str | Path | None = None,
    *,
    title: str = "Select folder",
) -> str | None:
    """
    Open the OS folder picker and return the selected path.

    Returns None when the user cancels or the picker is unavailable.

    Streamlit reruns scripts off the main thread, so tkinter is launched in a
    short-lived child process where it owns the GUI main loop.
    """
    initial = _resolve_initial_dir(initial_dir)
    try:
        return _browse_folder_subprocess(initial, title)
    except Exception as exc:
        logger.warning("Folder picker failed: %s", exc)
        return None


def _browse_folder_subprocess(initial: str | None, title: str) -> str | None:
    try:
        import tkinter  # noqa: F401
    except ImportError:
        return None

    args = [sys.executable, "-c", _PICKER_SCRIPT, title, initial or ""]
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.warning("Folder picker subprocess failed: %s", exc)
        return None

    if completed.returncode != 0 and completed.stderr:
        logger.debug("Folder picker stderr: %s", completed.stderr.strip())

    selected = (completed.stdout or "").strip()
    if not selected:
        return None
    return str(Path(selected).resolve())


def _resolve_initial_dir(initial_dir: str | Path | None) -> str | None:
    if not initial_dir:
        return None
    path = Path(initial_dir)
    if path.is_dir():
        return str(path)
    parent = path.parent
    if parent.is_dir():
        return str(parent)
    return None
