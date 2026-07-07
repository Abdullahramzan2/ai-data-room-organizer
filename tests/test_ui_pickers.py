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


@patch("dataroom.ui.pickers.subprocess.run")
def test_browse_folder_returns_selected_path(mock_run, tmp_path: Path):
    mock_run.return_value = MagicMock(stdout=str(tmp_path) + "\n", returncode=0, stderr="")

    result = browse_folder(title="Pick")

    assert result == str(tmp_path.resolve())
    mock_run.assert_called_once()


@patch("dataroom.ui.pickers.subprocess.run")
def test_browse_folder_returns_none_when_cancelled(mock_run):
    mock_run.return_value = MagicMock(stdout="", returncode=0, stderr="")

    assert browse_folder() is None


@patch("dataroom.ui.pickers.subprocess.run", side_effect=OSError("spawn failed"))
def test_browse_folder_returns_none_on_subprocess_error(mock_run):
    assert browse_folder() is None
