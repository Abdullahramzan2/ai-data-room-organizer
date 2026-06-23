"""Tests for dataroom doctor health checks."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from dataroom.cli import main
from dataroom.doctor.checks import (
    _check_embedding_model,
    _check_ollama,
    _check_poppler,
    _check_tesseract,
    format_doctor_report,
    run_doctor,
)
from dataroom.settings import Settings


def test_check_tesseract_skip_when_disabled():
    result = _check_tesseract({"enabled": False})
    assert result.status == "skip"


def test_check_tesseract_warn_when_missing(tmp_path: Path):
    result = _check_tesseract({"enabled": True, "tesseract_cmd": str(tmp_path / "missing.exe")})
    assert result.status == "warn"
    assert result.fix


def test_check_poppler_pass_when_pdftoppm_on_path(monkeypatch, tmp_path: Path):
    bin_dir = tmp_path / "poppler"
    bin_dir.mkdir()
    (bin_dir / "pdftoppm.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        "dataroom.doctor.checks.resolve_poppler_path",
        lambda _configured: str(bin_dir),
    )
    result = _check_poppler({"enabled": True})
    assert result.status == "pass"


@patch("sentence_transformers.SentenceTransformer")
def test_check_embedding_model_pass(mock_st):
    mock_model = MagicMock()
    mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
    mock_st.return_value = mock_model

    result = _check_embedding_model("all-MiniLM-L6-v2")
    assert result.status == "pass"
    assert "3 dimensions" in result.message


@patch("sentence_transformers.SentenceTransformer", side_effect=RuntimeError("download failed"))
def test_check_embedding_model_fail(_mock_st):
    result = _check_embedding_model("missing-model")
    assert result.status == "fail"
    assert result.fix


def test_check_ollama_skip_in_local_mode():
    settings = Settings(classification_mode="local")
    result = _check_ollama(settings, {"classification": {"reasoning_provider": "ollama"}})
    assert result.status == "skip"


def test_format_doctor_report_lists_fixes():
    report = run_doctor()
    text = format_doctor_report(report)
    assert "environment check" in text
    assert "[OK]" in text or "[WARN]" in text or "[FAIL]" in text


@patch("dataroom.cli.run_doctor")
def test_doctor_cli_json(mock_run_doctor):
    from dataroom.doctor.models import CheckResult, DoctorReport

    mock_run_doctor.return_value = DoctorReport(
        checks=[
            CheckResult(
                name="embedding_model",
                status="pass",
                message="ok",
            )
        ]
    )

    runner = CliRunner()
    result = runner.invoke(main, ["doctor", "--json"])
    assert result.exit_code == 0
    assert '"checks"' in result.output


@patch("dataroom.cli.run_doctor")
def test_doctor_cli_exits_on_failure(mock_run_doctor):
    from dataroom.doctor.models import CheckResult, DoctorReport

    mock_run_doctor.return_value = DoctorReport(
        checks=[
            CheckResult(
                name="python",
                status="fail",
                message="too old",
                fix="upgrade",
            )
        ]
    )

    runner = CliRunner()
    result = runner.invoke(main, ["doctor"])
    assert result.exit_code == 1
    assert "too old" in result.output
