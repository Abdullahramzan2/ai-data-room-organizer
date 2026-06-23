"""Tests for static HTML index export."""

from pathlib import Path

from dataroom.export.html_index import (
    build_index_entries,
    path_to_file_url,
    resolve_link_target,
    write_html_index,
)


def _row(**overrides) -> dict[str, str]:
    base = {
        "file_name": "report.pdf",
        "original_path": "C:/source/report.pdf",
        "output_path": "C:/out/05_Env/report.pdf",
        "category_folder": "05_Environmental_RCRA_BRAC_FOSET",
        "confidence": "high",
        "score": "0.95",
        "modified_at": "2026-06-01T12:00:00+00:00",
        "classification_reason": "Matched keywords: brac",
        "needs_review": "false",
    }
    base.update(overrides)
    return base


def test_path_to_file_url(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("x", encoding="utf-8")
    url = path_to_file_url(str(file_path))
    assert url.startswith("file:///")
    assert "sample.txt" in url


def test_resolve_link_target_modes(tmp_path: Path):
    row = _row()
    output_dir = tmp_path / "data_room"
    assert resolve_link_target(row, "original", output_dir) == "C:/source/report.pdf"
    assert resolve_link_target(row, "organized", output_dir) == "C:/out/05_Env/report.pdf"


def test_build_index_entries_relative_mode(tmp_path: Path):
    output_dir = tmp_path / "data_room"
    output_dir.mkdir()
    row = _row(output_path=str(output_dir / "05_Env" / "report.pdf"))
    entries = build_index_entries([row], link_mode="relative", output_dir=output_dir)
    assert entries[0]["link_url"] == "05_Env/report.pdf"


def test_write_html_index(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    rows = [_row(output_path=str(output_dir / "05_Env" / "report.pdf"))]
    index_path = output_dir / "index.html"
    write_html_index(index_path, rows, link_mode="original", output_dir=output_dir)

    content = index_path.read_text(encoding="utf-8")
    assert "<title>Data Room Index</title>" in content
    assert "report.pdf" in content
    assert "category_folder" in content
    assert "function render()" in content
