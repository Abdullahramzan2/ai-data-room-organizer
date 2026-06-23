"""Tests for UI CLI entrypoint."""

import builtins
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dataroom.cli import main


def test_ui_command_requires_streamlit(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "streamlit" or name.startswith("streamlit."):
            raise ImportError("streamlit not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    runner = CliRunner()
    result = runner.invoke(main, ["ui"])
    assert result.exit_code != 0
    assert "ui" in result.output.lower()


def test_ui_command_launches_streamlit():
    import sys

    mock_st_main = MagicMock()
    mock_cli = MagicMock()
    mock_cli.main = mock_st_main
    mock_web = MagicMock()
    mock_web.cli = mock_cli
    mock_st = MagicMock()
    mock_st.web = mock_web

    with patch.dict(
        sys.modules,
        {
            "streamlit": mock_st,
            "streamlit.web": mock_web,
            "streamlit.web.cli": mock_cli,
        },
    ):
        runner = CliRunner()
        result = runner.invoke(main, ["ui", "--port", "9999"])
    assert result.exit_code == 0
    mock_st_main.assert_called_once()
