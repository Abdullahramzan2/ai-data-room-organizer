"""Tests for admin artifact mirroring into 00_Admin_and_Index."""

from pathlib import Path

from dataroom.export.admin_outputs import admin_folder_name, mirror_admin_artifacts


def test_admin_folder_name_default():
    assert admin_folder_name({}) == "00_Admin_and_Index"
    assert admin_folder_name({"output": {"admin_folder": "99_Custom"}}) == "99_Custom"


def test_mirror_admin_artifacts_copies_files(tmp_path: Path):
    output_dir = tmp_path / "data_room"
    output_dir.mkdir()
    manifest = output_dir / "manifest.csv"
    manifest.write_text("file_name\nx.pdf\n", encoding="utf-8")
    index_html = output_dir / "index.html"
    index_html.write_text("<html></html>", encoding="utf-8")

    config = {"output": {"mirror_admin_artifacts": True, "admin_folder": "00_Admin_and_Index"}}
    mirrored = mirror_admin_artifacts(
        output_dir,
        config,
        {
            "manifest": manifest,
            "index_html": index_html,
        },
    )

    admin_dir = output_dir / "00_Admin_and_Index"
    assert (admin_dir / "manifest.csv").read_text(encoding="utf-8") == manifest.read_text(encoding="utf-8")
    assert (admin_dir / "index.html").is_file()
    assert len(mirrored) == 2
    assert manifest.read_text(encoding="utf-8")  # root copy preserved


def test_mirror_admin_artifacts_disabled(tmp_path: Path):
    output_dir = tmp_path / "data_room"
    output_dir.mkdir()
    manifest = output_dir / "manifest.csv"
    manifest.write_text("x", encoding="utf-8")

    mirrored = mirror_admin_artifacts(
        output_dir,
        {"output": {"mirror_admin_artifacts": False}},
        {"manifest": manifest},
    )
    assert mirrored == []
    assert not (output_dir / "00_Admin_and_Index").exists()
