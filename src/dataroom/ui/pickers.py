"""Native folder picker for local Streamlit UI (Windows/desktop)."""

from __future__ import annotations

from pathlib import Path


def browse_folder(
    initial_dir: str | Path | None = None,
    *,
    title: str = "Select folder",
) -> str | None:
    """
    Open the OS folder picker and return the selected path.

    Returns None when the user cancels or the picker is unavailable.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        return None

    initial = _resolve_initial_dir(initial_dir)
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        kwargs: dict[str, str] = {"title": title}
        if initial is not None:
            kwargs["initialdir"] = initial
        selected = filedialog.askdirectory(**kwargs)
    finally:
        root.destroy()

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
