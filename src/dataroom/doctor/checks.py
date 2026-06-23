"""Individual environment checks and orchestration for dataroom doctor."""

from __future__ import annotations

import importlib
import logging
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dataroom.classification.mode import tier3_enabled
from dataroom.classification.providers.enterprise_provider import EnterpriseReasoningProvider
from dataroom.classification.providers.ollama_provider import OllamaReasoningProvider
from dataroom.config import load_app_config
from dataroom.doctor.models import CheckResult, DoctorReport
from dataroom.ingestion.extractors.legacy_office import (
    LegacyOfficeConfig,
    resolve_libreoffice_cmd,
)
from dataroom.ocr.tesseract import OcrConfig, TesseractOcr, resolve_poppler_path, resolve_tesseract_cmd
from dataroom.settings import Settings, get_settings

logger = logging.getLogger(__name__)

_STATUS_ICONS = {
    "pass": "OK",
    "warn": "WARN",
    "fail": "FAIL",
    "skip": "SKIP",
}


def _check_python() -> CheckResult:
    version = sys.version_info
    version_text = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 11):
        return CheckResult(
            name="python",
            status="pass",
            message=f"Python {version_text}",
        )
    return CheckResult(
        name="python",
        status="fail",
        message=f"Python {version_text} (requires 3.11+)",
        fix="Install Python 3.11 or newer and recreate your virtual environment.",
    )


def _check_import(module_name: str, label: str) -> CheckResult:
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return CheckResult(
            name=f"package:{module_name}",
            status="fail",
            message=f"{label} is not installed ({exc})",
            fix="Run: pip install -e . from the project root.",
        )
    return CheckResult(
        name=f"package:{module_name}",
        status="pass",
        message=f"{label} importable",
    )


def _check_tesseract(ocr_cfg: dict[str, Any]) -> CheckResult:
    if not ocr_cfg.get("enabled", True):
        return CheckResult(
            name="tesseract",
            status="skip",
            message="OCR disabled in config",
        )

    binary = resolve_tesseract_cmd(ocr_cfg.get("tesseract_cmd"))
    if not binary or not Path(binary).is_file():
        return CheckResult(
            name="tesseract",
            status="warn",
            message="Tesseract OCR not found",
            fix=(
                "Install Tesseract and add it to PATH, or set ocr.tesseract_cmd in config/default.yaml. "
                "On Windows: winget install --id UB-Mannheim.TesseractOCR"
            ),
        )

    ocr = TesseractOcr(
        OcrConfig(
            enabled=True,
            tesseract_cmd=binary,
            poppler_path=ocr_cfg.get("poppler_path"),
        )
    )
    if ocr.is_available():
        return CheckResult(
            name="tesseract",
            status="pass",
            message=f"Tesseract available at {binary}",
        )
    return CheckResult(
        name="tesseract",
        status="warn",
        message=f"Tesseract binary found but not usable: {binary}",
        fix="Verify the Tesseract install and language packs (ocr.language in config).",
    )


def _check_poppler(ocr_cfg: dict[str, Any]) -> CheckResult:
    if not ocr_cfg.get("enabled", True):
        return CheckResult(
            name="poppler",
            status="skip",
            message="OCR disabled in config",
        )

    poppler_path = resolve_poppler_path(ocr_cfg.get("poppler_path"))
    if not poppler_path:
        return CheckResult(
            name="poppler",
            status="warn",
            message="Poppler (pdftoppm) not found",
            fix=(
                "Install Poppler and add it to PATH, or set ocr.poppler_path in config/default.yaml. "
                "On Windows: winget install --id oschwartz10612.Poppler"
            ),
        )

    bin_dir = Path(poppler_path)
    pdftoppm = bin_dir / ("pdftoppm.exe" if sys.platform == "win32" else "pdftoppm")
    if not pdftoppm.is_file():
        found = shutil.which("pdftoppm")
        if not found:
            return CheckResult(
                name="poppler",
                status="warn",
                message=f"Poppler directory set but pdftoppm missing: {poppler_path}",
                fix="Point ocr.poppler_path at the Poppler bin folder containing pdftoppm.",
            )
        poppler_path = str(Path(found).parent)

    return CheckResult(
        name="poppler",
        status="pass",
        message=f"Poppler available at {poppler_path}",
    )


def _check_libreoffice(legacy_cfg: dict[str, Any]) -> CheckResult:
    binary = resolve_libreoffice_cmd(legacy_cfg.get("libreoffice_cmd"))
    if binary:
        return CheckResult(
            name="libreoffice",
            status="pass",
            message=f"LibreOffice available at {binary}",
        )
    return CheckResult(
        name="libreoffice",
        status="warn",
        message="LibreOffice not found (legacy .doc / .ppt conversion)",
        fix=(
            "Install LibreOffice or set legacy_office.libreoffice_cmd in config/default.yaml. "
            "Word/PowerPoint COM may still work on Windows."
        ),
    )


def _check_embedding_model(model_name: str) -> CheckResult:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        return CheckResult(
            name="embedding_model",
            status="fail",
            message=f"sentence-transformers not installed ({exc})",
            fix="Run: pip install -e .",
        )

    try:
        model = SentenceTransformer(model_name)
        vector = model.encode(["health check"], normalize_embeddings=True)
        dim = len(vector[0])
    except Exception as exc:
        logger.debug("Embedding model check failed: %s", exc)
        return CheckResult(
            name="embedding_model",
            status="fail",
            message=f"Could not load embedding model '{model_name}': {exc}",
            fix=(
                "Check classification.embedding_model in config/default.yaml and network access "
                "for the first Hugging Face download."
            ),
        )

    return CheckResult(
        name="embedding_model",
        status="pass",
        message=f"Embedding model '{model_name}' loaded ({dim} dimensions)",
    )


def _ping_openai_compatible(base_url: str, api_key: str, timeout: float = 5.0) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return True, "reachable"
            return False, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            return True, "reachable (auth required)"
        return False, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, str(exc)


def _check_ollama(settings: Settings, config: dict[str, Any]) -> CheckResult:
    if not tier3_enabled(settings):
        return CheckResult(
            name="ollama",
            status="skip",
            message="Tier 3 disabled (CLASSIFICATION_MODE=local)",
        )

    class_cfg = config.get("classification", {}) or {}
    provider = (class_cfg.get("reasoning_provider") or settings.reasoning_provider or "auto").lower()
    chain = class_cfg.get("auto_provider_chain") or []
    relevant = provider == "ollama" or (provider == "auto" and "ollama" in chain)
    if not relevant:
        return CheckResult(
            name="ollama",
            status="skip",
            message="Ollama not in active provider selection",
        )

    ollama = OllamaReasoningProvider(settings)
    if ollama.is_available():
        return CheckResult(
            name="ollama",
            status="pass",
            message=f"Ollama reachable at {settings.ollama_base_url} (model: {settings.ollama_model})",
        )
    return CheckResult(
        name="ollama",
        status="warn",
        message=f"Ollama not reachable at {settings.ollama_base_url}",
        fix=(
            "Start Ollama (ollama serve) and pull the configured model "
            f"(ollama pull {settings.ollama_model}), or change REASONING_PROVIDER / auto_provider_chain."
        ),
    )


def _check_enterprise(settings: Settings, config: dict[str, Any]) -> CheckResult:
    if not tier3_enabled(settings):
        return CheckResult(
            name="enterprise",
            status="skip",
            message="Tier 3 disabled (CLASSIFICATION_MODE=local)",
        )

    class_cfg = config.get("classification", {}) or {}
    provider = (class_cfg.get("reasoning_provider") or settings.reasoning_provider or "auto").lower()
    chain = class_cfg.get("auto_provider_chain") or []
    relevant = provider == "enterprise" or (provider == "auto" and "enterprise" in chain)
    configured = bool(settings.enterprise_api_key and settings.enterprise_base_url and settings.enterprise_model)

    if not relevant and not configured:
        return CheckResult(
            name="enterprise",
            status="skip",
            message="Enterprise LLM not configured",
        )

    enterprise = EnterpriseReasoningProvider(settings)
    if not enterprise.is_available():
        return CheckResult(
            name="enterprise",
            status="warn",
            message="Enterprise LLM credentials incomplete",
            fix=(
                "Set ENTERPRISE_API_KEY, ENTERPRISE_BASE_URL, and ENTERPRISE_MODEL in .env, "
                "or remove enterprise from auto_provider_chain."
            ),
        )

    ok, detail = _ping_openai_compatible(
        settings.enterprise_base_url or "",
        settings.enterprise_api_key or "",
        timeout=settings.enterprise_timeout,
    )
    if ok:
        return CheckResult(
            name="enterprise",
            status="pass",
            message=f"Enterprise endpoint reachable at {settings.enterprise_base_url} ({detail})",
        )
    return CheckResult(
        name="enterprise",
        status="warn",
        message=f"Enterprise endpoint not reachable: {detail}",
        fix="Verify ENTERPRISE_BASE_URL, VPN/firewall access, and API key permissions.",
    )


def run_doctor(
    config_path: Path | None = None,
    *,
    settings: Settings | None = None,
) -> DoctorReport:
    """Run all environment health checks."""
    config = load_app_config(config_path)
    settings = settings or get_settings()
    ocr_cfg = config.get("ocr", {}) or {}
    legacy_cfg = config.get("legacy_office", {}) or {}
    class_cfg = config.get("classification", {}) or {}
    embedding_model = str(class_cfg.get("embedding_model", "all-MiniLM-L6-v2"))

    checks: list[CheckResult] = [
        _check_python(),
        _check_import("click", "Click"),
        _check_import("yaml", "PyYAML"),
        _check_import("fitz", "PyMuPDF"),
        _check_import("openpyxl", "openpyxl"),
        _check_tesseract(ocr_cfg),
        _check_poppler(ocr_cfg),
        _check_libreoffice(legacy_cfg),
        _check_embedding_model(embedding_model),
        _check_ollama(settings, config),
        _check_enterprise(settings, config),
    ]
    return DoctorReport(checks=checks)


def format_doctor_report(report: DoctorReport) -> str:
    """Render a human-readable doctor report."""
    lines: list[str] = ["Data Room Organizer — environment check", ""]
    for check in report.checks:
        icon = _STATUS_ICONS.get(check.status, check.status.upper())
        lines.append(f"[{icon}] {check.name}: {check.message}")
        if check.fix and check.status in {"warn", "fail"}:
            lines.append(f"      Fix: {check.fix}")
    lines.append("")
    if report.has_failures:
        lines.append("One or more required checks failed.")
    else:
        lines.append("No blocking failures detected.")
    return "\n".join(lines)
