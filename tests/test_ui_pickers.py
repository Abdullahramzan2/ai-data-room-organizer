"""Tests for native folder picker helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from dataroom.ui.pickers import _resolve_initial_dir, browse_folder


def test_resolve_initial_dir_prefers_existing_directory(tmp_path: Path):
    folder = tmp_path / "data"
    folder.mkdir()
    assert _resolve_initial_dir(folder) == str(folder)


def test_resolve_initial_dir_uses_parent_for_file_path(tmp_path: Path):
    parent = tmp_path / "data"
    parent.mkdir()
    file_path = parent / "doc.txt"
    file_path.write_text("x", encoding="utf-8")
    assert _resolve_initial_dir(file_path) == str(parent)


@patch("tkinter.filedialog.askdirectory")
@patch("tkinter.Tk")
def test_browse_folder_returns_selected_path(mock_tk, mock_askdirectory, tmp_path: Path):
    mock_root = MagicMock()
    mock_tk.return_value = mock_root
    mock_askdirectory.return_value = str(tmp_path)

    result = browse_folder(title="Pick")

    assert result == str(tmp_path.resolve())
    mock_root.destroy.assert_called_once()


@patch("tkinter.filedialog.askdirectory")
@patch("tkinter.Tk")
def test_browse_folder_returns_none_when_cancelled(mock_tk, mock_askdirectory):
    mock_root = MagicMock()
    mock_tk.return_value = mock_root
    mock_askdirectory.return_value = ""

    assert browse_folder() is None
