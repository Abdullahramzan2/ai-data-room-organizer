"""Tests for file hashing."""

from dataroom.ingestion.hashing import sha256_file


def test_sha256_file(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_bytes(b"hello")
    digest = sha256_file(path)
    assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
