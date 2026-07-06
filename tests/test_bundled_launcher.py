from pathlib import Path
import sys
from unittest.mock import patch

from dataroom.bundled_launcher import (
    apply_bundled_environment,
    build_doctor_command,
    build_ui_command,
    bundled_python_executable,
    ensure_user_env_file,
    is_doctor_launcher,
    launch_doctor,
    launch_ui,
    pause_doctor_console,
    resolve_install_root_from_launcher,
    tool_bin_paths,
)
from dataroom.paths import resolve_dev_project_root


def _stage_bundle(tmp_path: Path) -> Path:
    install = tmp_path / "install"
    launcher_dir = install / "launcher"
    app = install / "app"
    python_dir = install / "python"
    tools = install / "tools"
    models = install / "models" / "huggingface"

    launcher_dir.mkdir(parents=True)
    (launcher_dir / "DataRoomOrganizer.exe").write_bytes(b"stub")
    (app / "config").mkdir(parents=True)
    (app / ".env.example").write_text("CLASSIFICATION_MODE=local\n", encoding="utf-8")
    python_dir.mkdir(parents=True)
    (python_dir / "python.exe").write_text("stub", encoding="utf-8")

    pop_dir = tools / "poppler" / "Library" / "bin"
    pop_dir.mkdir(parents=True)
    (pop_dir / "pdftoppm.exe").write_text("stub", encoding="utf-8")

    models.mkdir(parents=True)
    return install


def test_find_install_root_near_walks_up_from_dist(tmp_path):
    install = _stage_bundle(tmp_path)
    dist = install / "packaging" / "dist"
    dist.mkdir(parents=True)
    fake_exe = dist / "DataRoomOrganizer.exe"
    fake_exe.write_bytes(b"stub")
    from dataroom.bundled_launcher import find_install_root_near

    assert find_install_root_near(fake_exe) == install.resolve()


def test_resolve_install_root_from_launcher_path(tmp_path):
    install = _stage_bundle(tmp_path)
    launcher = install / "launcher" / "DataRoomOrganizer.exe"
    assert resolve_install_root_from_launcher(launcher) == install.resolve()


def test_resolve_install_root_override(tmp_path):
    install = _stage_bundle(tmp_path)
    assert resolve_install_root_from_launcher(override=install) == install.resolve()


def test_resolve_install_root_missing_override_shows_help(tmp_path):
    missing = tmp_path / "missing-install"
    try:
        resolve_install_root_from_launcher(override=missing)
        assert False, "expected FileNotFoundError"
    except FileNotFoundError as exc:
        assert "stage_dev_install.ps1" in str(exc)


def test_resolve_install_root_dev_mode(monkeypatch):
    monkeypatch.delenv("DATAROOM_HOME", raising=False)
    root = resolve_install_root_from_launcher(dev=True)
    assert root == resolve_dev_project_root()


def test_resolve_install_root_defaults_to_dev_from_source(monkeypatch):
    monkeypatch.delenv("DATAROOM_HOME", raising=False)
    root = resolve_install_root_from_launcher()
    assert root == resolve_dev_project_root()


def test_bundled_python_executable_dev_uses_current_interpreter(tmp_path):
    install = _stage_bundle(tmp_path)
    assert bundled_python_executable(install, dev=True) == Path(sys.executable).resolve()
    assert bundled_python_executable(install, dev=False) == (install / "python" / "python.exe").resolve()


def test_apply_bundled_environment_sets_paths(tmp_path):
    install = _stage_bundle(tmp_path)
    env = apply_bundled_environment(install)

    assert env["DATAROOM_HOME"] == str(install.resolve())
    assert env["DATAROOM_BUNDLED"] == "1"
    assert env["HF_HOME"] == str((install / "models" / "huggingface").resolve())
    assert str(install / "tools" / "poppler" / "Library" / "bin") in env["PATH"]


def test_tool_bin_paths_collects_existing_dirs(tmp_path):
    install = _stage_bundle(tmp_path)
    bins = tool_bin_paths(install)
    assert str((install / "tools" / "poppler" / "Library" / "bin").resolve()) in bins


def test_bundled_python_executable_prefers_venv_scripts(tmp_path):
    install = _stage_bundle(tmp_path)
    scripts_python = install / "python" / "Scripts" / "python.exe"
    scripts_python.parent.mkdir(parents=True, exist_ok=True)
    scripts_python.write_text("stub", encoding="utf-8")
    (install / "python" / "pyvenv.cfg").write_text("home = .\n", encoding="utf-8")
    assert bundled_python_executable(install) == scripts_python.resolve()


def test_bundled_python_executable(tmp_path):
    install = _stage_bundle(tmp_path)
    assert bundled_python_executable(install) == (install / "python" / "python.exe").resolve()


def test_build_commands(tmp_path):
    install = _stage_bundle(tmp_path)
    python = str((install / "python" / "python.exe").resolve())
    assert build_ui_command(install) == [python, "-m", "dataroom.ui.launch"]
    assert build_doctor_command(install) == [python, "-m", "dataroom.cli", "doctor"]


def test_ensure_user_env_file_creates_from_example(tmp_path, monkeypatch):
    install = _stage_bundle(tmp_path)
    appdata = tmp_path / "appdata"
    monkeypatch.setenv("DATAROOM_HOME", str(install))
    monkeypatch.setenv("APPDATA", str(appdata))

    env_path = ensure_user_env_file()
    assert env_path == appdata / "DataRoomOrganizer" / ".env"
    assert env_path.is_file()
    assert "CLASSIFICATION_MODE=local" in env_path.read_text(encoding="utf-8")


def test_launch_ui_invokes_subprocess(tmp_path, monkeypatch):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    with (
        patch("dataroom.bundled_launcher.schedule_browser_open") as browser,
        patch("dataroom.bundled_launcher.run_managed_subprocess", return_value=0) as run,
    ):
        code = launch_ui(install, open_browser=True)

    assert code == 0
    browser.assert_called_once()
    run.assert_called_once()


def test_run_managed_subprocess_handles_keyboard_interrupt():
    from dataroom.bundled_launcher import run_managed_subprocess

    class FakeProc:
        def __init__(self):
            self._wait_calls = 0

        def wait(self, timeout=None):
            self._wait_calls += 1
            if self._wait_calls == 1:
                raise KeyboardInterrupt
            return 0

        def terminate(self):
            pass

        def kill(self):
            pass

    with patch("dataroom.bundled_launcher.subprocess.Popen", return_value=FakeProc()):
        code = run_managed_subprocess(["python"], env={}, cwd=".")

    assert code == 0


def test_launch_doctor_invokes_subprocess(tmp_path, monkeypatch):
    install = _stage_bundle(tmp_path)
    monkeypatch.setenv("DATAROOM_HOME", str(install))

    with patch("dataroom.bundled_launcher.run_managed_subprocess", return_value=0) as run:
        code = launch_doctor(install)

    assert code == 0
    run.assert_called_once()


def test_pause_doctor_console_noop_when_not_frozen(monkeypatch):
    monkeypatch.setattr("dataroom.bundled_launcher.is_doctor_launcher", lambda: False)
    pause_doctor_console()


def test_is_doctor_launcher_false_for_source_python():
    assert is_doctor_launcher() is False
