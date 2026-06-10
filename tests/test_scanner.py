from pathlib import Path

from dataroom.ingestion.scanner import normalize_extensions, scan_folder


def test_normalize_extensions():
    assert normalize_extensions(["pdf", ".DOCX", "txt"]) == {".pdf", ".docx", ".txt"}


def test_scan_folder_recursive(tmp_path: Path):
    (tmp_path / "a.pdf").write_text("pdf")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("hello")
    (tmp_path / "skip.exe").write_text("no")

    files = scan_folder(tmp_path, [".pdf", ".txt"], recursive=True)
    names = {f.name for f in files}
    assert names == {"a.pdf", "b.txt"}


def test_scan_folder_non_recursive(tmp_path: Path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.pdf").write_text("pdf")
    (sub / "b.pdf").write_text("pdf")

    files = scan_folder(tmp_path, [".pdf"], recursive=False)
    assert len(files) == 1
    assert files[0].name == "a.pdf"
