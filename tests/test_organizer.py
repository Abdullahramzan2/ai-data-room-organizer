from pathlib import Path

from dataroom.organizer import organize_files

MINI_TAXONOMY = {
    "categories": [
        {"id": "02", "folder": "02_Land_Control"},
        {"id": "19", "folder": "19_Unclassified_Review_Queue"},
    ]
}


def test_copy_into_category_folder(tmp_path: Path):
    source = tmp_path / "input" / "psa.txt"
    source.parent.mkdir()
    source.write_text("purchase and sale", encoding="utf-8")
    output_dir = tmp_path / "data_room"

    rows = [
        {
            "source_path": str(source),
            "category_folder": "02_Land_Control",
        }
    ]
    results = organize_files(rows, output_dir, MINI_TAXONOMY)

    assert len(results) == 1
    assert results[0].dest_path == output_dir / "02_Land_Control" / "psa.txt"
    assert results[0].dest_path.read_text(encoding="utf-8") == "purchase and sale"
    assert source.read_text(encoding="utf-8") == "purchase and sale"


def test_rename_uses_standardized_name(tmp_path: Path):
    source = tmp_path / "report.pdf"
    source.write_bytes(b"pdf")
    output_dir = tmp_path / "out"

    rows = [{"source_path": str(source), "category_folder": "02_Land_Control"}]
    results = organize_files(rows, output_dir, MINI_TAXONOMY, rename=True)

    assert results[0].dest_path.name.startswith("unknown-date__Land_Control__report.pdf")
