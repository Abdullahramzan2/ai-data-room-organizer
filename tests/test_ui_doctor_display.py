"""Tests for doctor UI display helpers."""

from dataroom.ui.doctor_display import _check_label, _doctor_table_rows


class _FakeCheck:
    def __init__(self, name: str, status: str, message: str, fix: str | None = None):
        self.name = name
        self.status = status
        self.message = message
        self.fix = fix


def test_check_label_strips_package_prefix():
    assert _check_label("package:click") == "click"
    assert _check_label("tesseract") == "Tesseract"


def test_doctor_table_rows_maps_status():
    rows = _doctor_table_rows(
        [
            _FakeCheck("python", "pass", "Python 3.12.3"),
            _FakeCheck("libreoffice", "warn", "Not found", fix="Install LibreOffice"),
        ]
    )
    assert rows[0]["Status"] == "Pass"
    assert rows[1]["Status"] == "Warn"
    assert rows[1]["Check"] == "Libreoffice"
