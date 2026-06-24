"""Tests for source authentication matrix export."""

from pathlib import Path

from dataroom.export.source_auth_matrix import (
    SOURCE_AUTH_COLUMNS,
    build_source_authentication_rows,
    write_source_authentication_matrix,
)


def test_build_source_authentication_rows():
    rows = build_source_authentication_rows(
        [
            {
                "file_name": "a.pdf",
                "original_path": "C:/in/a.pdf",
                "file_hash": "abc123",
                "modified_at": "2026-01-01",
                "file_size": "100",
                "extraction_method": "native",
                "parse_status": "success",
                "category_folder": "02_Land_Control",
                "organize_status": "copied",
            }
        ]
    )
    assert rows[0]["file_hash"] == "abc123"
    assert list(rows[0].keys()) == SOURCE_AUTH_COLUMNS


def test_write_source_authentication_matrix(tmp_path: Path):
    path = tmp_path / "00_Admin_and_Index" / "source_authentication_matrix.csv"
    write_source_authentication_matrix(
        path,
        [{"file_name": "x.txt", "original_path": "C:/x.txt", "file_hash": "h1"}],
    )
    assert path.is_file()
    assert "file_hash" in path.read_text(encoding="utf-8")
