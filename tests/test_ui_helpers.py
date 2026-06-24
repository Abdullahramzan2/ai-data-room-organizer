"""Tests for Streamlit UI helpers (no Streamlit required)."""

from __future__ import annotations

import json
from pathlib import Path

from dataroom.config import load_taxonomy
from dataroom.ui.helpers import (
    list_output_artifacts,
    load_run_summary,
    review_queue_path,
    taxonomy_folder_names,
)


def test_taxonomy_folder_names():
    taxonomy = load_taxonomy()
    folders = taxonomy_folder_names(taxonomy)
    assert "01_Project_Overview" in folders
    assert len(folders) >= 10


def test_load_run_summary(tmp_path: Path):
    summary = {"processed": 3, "organized": 3}
    (tmp_path / "run_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    assert load_run_summary(tmp_path) == summary
    assert load_run_summary(tmp_path / "missing") is None


def test_list_output_artifacts(tmp_path: Path):
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    manifest = output_dir / "manifest.xlsx"
    manifest.write_text("x", encoding="utf-8")
    (output_dir / "run_summary.json").write_text(
        json.dumps({"manifest": str(manifest), "processed": 1}),
        encoding="utf-8",
    )

    artifacts = list_output_artifacts(output_dir)
    manifest_row = next(a for a in artifacts if a["artifact"] == "manifest.xlsx")
    assert manifest_row["exists"] == "yes"
    assert manifest_row["path"] == str(manifest)


def test_review_queue_path(tmp_path: Path):
    path = review_queue_path(tmp_path)
    assert path.name == "review_queue.xlsx"
    assert path.parent == tmp_path
