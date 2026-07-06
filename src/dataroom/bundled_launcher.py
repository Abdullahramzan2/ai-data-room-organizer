"""Launch bundled installs: environment setup, UI, and doctor."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from dataroom.paths import env_example_path, resolve_dev_project_root, resolve_env_file, user_config_dir

DEFAULT_UI_PORT = 8501
DEFAULT_UI_URL = f"http://127.0.0.1:{DEFAULT_UI_PORT}"

_TOOL_BIN_DIRS = (
    "tesseract",
    "poppler/Library/bin",
    "poppler/bin",
    "libreoffice/program",
)


_INSTALL_INCOMPLETE_MSG = (
    "Data Room Organizer is not fully installed next to this launcher.\n\n"
    "Expected folders beside the launcher:\n"
    "  app\\       python\\\n\n"
    "If you are developing locally, run:\n"
    "  packaging\\stage_dev_install.ps1\n"
    "then open:\n"
    "  packaging\\dev-install\\launcher\\DataRoomOrganizer.exe\n\n"
    "The copy in packaging\\dist\\ is only a build artifact until the full installer is created."
)


def find_install_root_near(executable: Path) -> Path | None:
    """Locate a bundled install directory relative to a launcher executable."""
    if executable.parent.name.lower() == "launcher":
        candidate = executable.parent.parent
        if is_bundled_install_root(candidate):
            return candidate.resolve()

    for directory in (executable.parent, *executable.parents):
        if is_bundled_install_root(directory):
            return directory.resolve()
    return None


def show_launcher_error(message: str) -> None:
    """Show a visible error for windowed (no-console) launcher builds."""
    log_path = Path(os.environ.get("TEMP", ".")) / "DataRoomOrganizer-launcher.log"
    try:
        log_path.write_text(message.strip() + "\n", encoding="utf-8")
    except OSError:
        log_path = None

    display = message.strip()
    if log_path is not None:
        display += f"\n\nDetails saved to:\n{log_path}"

    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(  # type: ignore[attr-defined]
                0,
                display,
                "Data Room Organizer",
                0x10,
            )
        except Exception:
            pass

    print(display, file=sys.stderr)


def is_frozen_launcher() -> bool:
    """True when running from a PyInstaller-built executable."""
    return bool(getattr(sys, "frozen", False))


def is_doctor_launcher() -> bool:
    """True when running as the PyInstaller-built doctor executable."""
    return is_frozen_launcher() and Path(sys.executable).stem.lower() == "dataroomdoctor"


def pause_doctor_console() -> None:
    """Keep the doctor console open so shortcut users can read the report."""
    if not is_doctor_launcher():
        return
    try:
        input("\nPress Enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass


def resolve_install_root_from_launcher(
    launcher_path: Path | None = None,
    *,
    override: str | Path | None = None,
    dev: bool = False,
) -> Path:
    """Infer install root from ``--dev``, ``DATAROOM_HOME``, override, or launcher location."""
    if dev:
        return resolve_dev_project_root()

    if override:
        path = Path(override)
        if not path.is_dir():
            raise FileNotFoundError(
                f"Install root not found: {path}. "
                "Use --dev for local development, or run packaging/stage_dev_install.ps1 "
                "to create packaging/dev-install for bundled-mode testing."
            )
        return path.resolve()

    home = os.environ.get("DATAROOM_HOME", "").strip()
    if home:
        path = Path(home)
        if path.is_dir():
            return path.resolve()

    executable = Path(launcher_path or sys.executable).resolve()
    if is_frozen_launcher():
        executable = Path(sys.executable).resolve()

    found = find_install_root_near(executable)
    if found is not None:
        return found

    if not is_frozen_launcher():
        return resolve_dev_project_root()

    raise RuntimeError(_INSTALL_INCOMPLETE_MSG)


def tool_bin_paths(install_root: Path) -> list[str]:
    """Return tool bin directories to prepend to PATH."""
    tools = install_root / "tools"
    if not tools.is_dir():
        return []
    bins: list[str] = []
    for rel in _TOOL_BIN_DIRS:
        candidate = tools / rel
        if candidate.is_dir():
            bins.append(str(candidate.resolve()))
    return bins


def apply_bundled_environment(install_root: Path) -> dict[str, str]:
    """Build a subprocess environment for a bundled install."""
    env = os.environ.copy()
    install = str(install_root.resolve())
    env["DATAROOM_HOME"] = install
    env["DATAROOM_BUNDLED"] = "1"

    models = install_root / "models" / "huggingface"
    if models.is_dir():
        model_path = str(models.resolve())
        env["HF_HOME"] = model_path
        env["TRANSFORMERS_CACHE"] = model_path
        env["HF_HUB_CACHE"] = model_path

    prepend = tool_bin_paths(install_root)
    if prepend:
        existing = env.get("PATH", "")
        env["PATH"] = os.pathsep.join(prepend + ([existing] if existing else []))

    return env


def activate_bundled_environment(env: dict[str, str]) -> None:
    """Apply bundled environment variables to the current process."""
    for key in (
        "DATAROOM_HOME",
        "DATAROOM_BUNDLED",
        "HF_HOME",
        "TRANSFORMERS_CACHE",
        "HF_HUB_CACHE",
        "PATH",
    ):
        if key in env:
            os.environ[key] = env[key]


def bundled_python_executable(install_root: Path, *, dev: bool = False) -> Path:
    """Return Python executable for bundled or development launches."""
    if dev or not is_bundled_install_root(install_root):
        return Path(sys.executable).resolve()

    python_dir = install_root / "python"
    venv_cfg = python_dir / "pyvenv.cfg"
    if venv_cfg.is_file():
        candidates = (
            python_dir / "Scripts" / "python.exe",
            python_dir / "python.exe",
        )
    else:
        candidates = (
            python_dir / "python.exe",
            python_dir / "Scripts" / "python.exe",
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        f"Bundled Python not found under {python_dir}. "
        "Run packaging/build.ps1 or packaging/stage_dev_install.ps1 first."
    )


def is_bundled_install_root(install_root: Path) -> bool:
    """True when *install_root* uses the packaged installer layout."""
    app_dir = install_root / "app"
    python_dir = install_root / "python"
    if app_dir.is_dir() and python_dir.is_dir():
        return True
    if (install_root / "launcher").is_dir() and python_dir.is_dir():
        return True
    return False


def ensure_user_env_file() -> Path:
    """Create ``%APPDATA%\\DataRoomOrganizer\\.env`` from ``.env.example`` when missing."""
    config_dir = user_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    env_path = resolve_env_file()
    if env_path.is_file():
        return env_path
    example = env_example_path()
    if example.is_file():
        shutil.copy2(example, env_path)
    else:
        env_path.write_text("CLASSIFICATION_MODE=local\nREASONING_PROVIDER=auto\n", encoding="utf-8")
    return env_path


def build_ui_command(install_root: Path, *, dev: bool = False) -> list[str]:
    """Argv to start the Streamlit UI."""
    python = bundled_python_executable(install_root, dev=dev)
    return [str(python), "-m", "dataroom.ui.launch"]


def build_doctor_command(install_root: Path, *, dev: bool = False) -> list[str]:
    """Argv to run ``dataroom doctor``."""
    python = bundled_python_executable(install_root, dev=dev)
    return [str(python), "-m", "dataroom.cli", "doctor"]


def schedule_browser_open(url: str = DEFAULT_UI_URL, *, delay_seconds: float = 2.0) -> None:
    """Open the UI in the default browser after a short startup delay."""

    def _open() -> None:
        time.sleep(delay_seconds)
        webbrowser.open(url)

    threading.Thread(target=_open, daemon=True).start()


def resolve_working_directory(install_root: Path, *, dev: bool = False) -> str:
    """Return process working directory for UI/doctor subprocesses."""
    if dev:
        return str(install_root.resolve())
    app_root = install_root / "app"
    if app_root.is_dir():
        return str(app_root.resolve())
    return str(install_root.resolve())


def run_managed_subprocess(argv: list[str], *, env: dict[str, str], cwd: str) -> int:
    """Run a child process and shut it down cleanly on Ctrl+C."""
    proc = subprocess.Popen(argv, env=env, cwd=cwd)
    try:
        return int(proc.wait())
    except KeyboardInterrupt:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("\nStopped.", file=sys.stderr)
        return 0


def launch_ui(
    install_root: Path,
    *,
    open_browser: bool = True,
    env: dict[str, str] | None = None,
    dev: bool = False,
) -> int:
    """Start the Streamlit UI."""
    if dev:
        runtime_env = os.environ.copy()
    else:
        runtime_env = env or apply_bundled_environment(install_root)
        activate_bundled_environment(runtime_env)
        ensure_user_env_file()
    if open_browser:
        schedule_browser_open()
    return run_managed_subprocess(
        build_ui_command(install_root, dev=dev),
        env=runtime_env,
        cwd=resolve_working_directory(install_root, dev=dev),
    )


def launch_doctor(install_root: Path, *, env: dict[str, str] | None = None, dev: bool = False) -> int:
    """Run ``dataroom doctor``."""
    if is_doctor_launcher():
        print("Data Room Organizer - environment check")
        print(f"Install folder: {install_root.resolve()}")
    if dev:
        runtime_env = os.environ.copy()
    else:
        runtime_env = env or apply_bundled_environment(install_root)
        activate_bundled_environment(runtime_env)
        ensure_user_env_file()
    if is_doctor_launcher():
        try:
            python = bundled_python_executable(install_root, dev=dev)
            print(f"Python: {python}")
        except FileNotFoundError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
    return run_managed_subprocess(
        build_doctor_command(install_root, dev=dev),
        env=runtime_env,
        cwd=resolve_working_directory(install_root, dev=dev),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch the Data Room Organizer (bundled install).")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Use the current project/venv (default when running from source).",
    )
    parser.add_argument(
        "--install-root",
        type=Path,
        default=None,
        help="Bundled install root (e.g. packaging/dev-install after staging).",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run environment health check instead of launching the UI.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser tab when launching the UI.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if Path(sys.executable).stem.lower() == "dataroomdoctor":
        args.doctor = True

    dev_mode = args.dev or not is_frozen_launcher()
    if args.install_root is not None:
        dev_mode = False

    doctor_console = args.doctor and is_doctor_launcher()
    exit_code = 1
    try:
        install_root = resolve_install_root_from_launcher(
            override=args.install_root,
            dev=dev_mode,
        )
        if is_frozen_launcher() and not dev_mode and not is_bundled_install_root(install_root):
            raise RuntimeError(_INSTALL_INCOMPLETE_MSG)

        if args.doctor:
            exit_code = launch_doctor(install_root, dev=dev_mode)
        else:
            exit_code = launch_ui(install_root, open_browser=not args.no_browser, dev=dev_mode)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        show_launcher_error(f"Launcher error: {exc}")
        exit_code = 1
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        exit_code = 0
    finally:
        if doctor_console:
            pause_doctor_console()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
