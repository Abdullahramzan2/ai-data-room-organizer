"""Tests for admin artifact paths under folder 00."""

from pathlib import Path

from dataroom.export.admin_outputs import (
    admin_folder_name,
    resolve_admin_artifact_paths,
    resolve_artifact_path,
)


def test_resolve_admin_artifact_paths_under_folder_00(tmp_path: Path):
    output_dir = tmp_path / "data_room"
    config = {"output": {"admin_folder": "00_Admin_and_Index"}}
    paths = resolve_admin_artifact_paths(output_dir, config)
    assert paths.manifest.parent.name == "00_Admin_and_Index"
    assert paths.source_auth_matrix.name == "source_authentication_matrix.xlsx"


def test_run_summary_not_copied_to_admin(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "run_summary.json").write_text("{}", encoding="utf-8")
    config = {"output": {"admin_folder": "00_Admin_and_Index"}}
    admin_dir = output_dir / "00_Admin_and_Index"
    admin_dir.mkdir()
    assert not (admin_dir / "run_summary.json").is_file()
    path = resolve_artifact_path(
        output_dir,
        config,
        summary_key=None,
        default_name="run_summary.json",
    )
    assert path == output_dir / "run_summary.json"


def test_resolve_artifact_path_prefers_admin_folder(tmp_path: Path):
    output_dir = tmp_path / "out"
    admin = output_dir / "00_Admin_and_Index"
    admin.mkdir(parents=True)
    (admin / "manifest.xlsx").write_text("x", encoding="utf-8")
    (output_dir / "manifest.xlsx").write_text("legacy", encoding="utf-8")
    path = resolve_artifact_path(
        output_dir,
        {"output": {}},
        summary_key="manifest",
        default_name="manifest.xlsx",
    )
    assert path.parent.name == "00_Admin_and_Index"
