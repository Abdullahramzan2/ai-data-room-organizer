"""Tests for admin artifact paths under folder 00."""

from pathlib import Path

from dataroom.export.admin_outputs import (
    admin_folder_name,
    copy_run_summary_to_admin,
    resolve_admin_artifact_paths,
    resolve_artifact_path,
)


def test_resolve_admin_artifact_paths_under_folder_00(tmp_path: Path):
    output_dir = tmp_path / "data_room"
    config = {"output": {"admin_folder": "00_Admin_and_Index"}}
    paths = resolve_admin_artifact_paths(output_dir, config)
    assert paths.manifest.parent.name == "00_Admin_and_Index"
    assert paths.source_auth_matrix.name == "source_authentication_matrix.csv"


def test_copy_run_summary_to_admin(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    (output_dir / "run_summary.json").write_text("{}", encoding="utf-8")
    config = {"output": {"admin_folder": "00_Admin_and_Index"}}
    dest = copy_run_summary_to_admin(output_dir, config)
    assert dest is not None
    assert dest.parent.name == "00_Admin_and_Index"


def test_resolve_artifact_path_prefers_admin_folder(tmp_path: Path):
    output_dir = tmp_path / "out"
    admin = output_dir / "00_Admin_and_Index"
    admin.mkdir(parents=True)
    (admin / "manifest.csv").write_text("x", encoding="utf-8")
    (output_dir / "manifest.csv").write_text("legacy", encoding="utf-8")
    path = resolve_artifact_path(
        output_dir,
        {"output": {}},
        summary_key="manifest",
        default_name="manifest.csv",
    )
    assert path.parent.name == "00_Admin_and_Index"
