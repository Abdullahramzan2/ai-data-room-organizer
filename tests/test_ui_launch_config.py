"""Tests for Streamlit launch configuration."""

from pathlib import Path

from dataroom.ui.launch_config import streamlit_argv


def test_streamlit_argv_disables_file_watcher():
    argv = streamlit_argv(Path("app.py"), port=9000)
    assert argv[0] == "streamlit"
    assert "run" in argv
    assert "--server.fileWatcherType" in argv
    assert argv[argv.index("--server.fileWatcherType") + 1] == "none"
    assert "--server.port" in argv
    assert argv[argv.index("--server.port") + 1] == "9000"
