"""Fallback extraction for legacy .doc and .ppt binary Office formats."""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from dataroom.paths import bundled_libreoffice_cmd
from dataroom.ocr.tesseract import TesseractOcr

logger = logging.getLogger(__name__)

# Word: wdFormatXMLDocument; PowerPoint: ppSaveAsOpenXMLPresentation
_COM_DOCX_FORMAT = 16
_COM_PPTX_FORMAT = 24

_LIBREOFFICE_WINDOWS_PATHS = (
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
)


def resolve_libreoffice_cmd(configured: str | None) -> str | None:
    """Return LibreOffice soffice path from config, bundle, PATH, or common Windows paths."""
    if configured:
        cmd = Path(configured)
        if cmd.is_file():
            return str(cmd)

    bundled = bundled_libreoffice_cmd()
    if bundled:
        return bundled

    found = shutil.which("soffice")
    if found:
        return found

    if platform.system() == "Windows":
        for candidate in _LIBREOFFICE_WINDOWS_PATHS:
            if Path(candidate).is_file():
                return candidate
    return None


@dataclass
class LegacyOfficeConfig:
    libreoffice_cmd: str | None = None
    enable_com: bool = True
    conversion_timeout: int = 120


@dataclass
class LegacyExtractionResult:
    text: str = ""
    page_count: int | None = None
    method: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class LegacyOfficeConverter:
    """Convert legacy Office files and extract text via multiple fallback strategies."""

    def __init__(
        self,
        config: LegacyOfficeConfig | None = None,
        ocr: TesseractOcr | None = None,
    ):
        self.config = config or LegacyOfficeConfig()
        self.ocr = ocr

    def extract_doc(self, path: Path, max_chars: int) -> LegacyExtractionResult:
        from dataroom.ingestion.extractors.office import read_docx_text

        result = LegacyExtractionResult()
        attempts: list[str] = []

        with tempfile.TemporaryDirectory(prefix="dataroom_doc_") as tmp:
            tmp_dir = Path(tmp)

            converted = self._convert_via_libreoffice(path, "docx", tmp_dir)
            if converted:
                attempts.append("libreoffice_docx")
                text, _truncated = read_docx_text(converted, max_chars)
                if text.strip():
                    result.text = text
                    result.method = "libreoffice_docx"
                    return result
                result.warnings.append("LibreOffice conversion produced empty DOCX text")

            if self.config.enable_com and platform.system() == "Windows":
                converted = self._convert_via_com(path, "docx", tmp_dir)
                if converted:
                    attempts.append("word_com_docx")
                    text, _truncated = read_docx_text(converted, max_chars)
                    if text.strip():
                        result.text = text
                        result.method = "word_com_docx"
                        return result
                    result.warnings.append("Word COM conversion produced empty DOCX text")

            for tool in ("antiword", "catdoc"):
                text = self._extract_via_cli_tool(path, tool)
                if text is not None:
                    attempts.append(tool)
                    if text.strip():
                        result.text = text[:max_chars]
                        result.method = tool
                        return result
                    result.warnings.append(f"{tool} returned empty text")

            ocr_text = self._ocr_via_pdf(path, tmp_dir, max_chars)
            if ocr_text:
                attempts.append("libreoffice_pdf_ocr")
                result.text = ocr_text
                result.method = "libreoffice_pdf_ocr"
                return result

        result.errors.append(
            "Could not extract .doc text. Tried: "
            + (", ".join(attempts) if attempts else "no methods available")
            + ". Install LibreOffice, Microsoft Word, antiword/catdoc, or enable OCR."
        )
        return result

    def extract_ppt(self, path: Path, max_chars: int) -> LegacyExtractionResult:
        from dataroom.ingestion.extractors.office import read_pptx_text

        result = LegacyExtractionResult()
        attempts: list[str] = []

        with tempfile.TemporaryDirectory(prefix="dataroom_ppt_") as tmp:
            tmp_dir = Path(tmp)

            converted = self._convert_via_libreoffice(path, "pptx", tmp_dir)
            if converted:
                attempts.append("libreoffice_pptx")
                text, page_count, _truncated = read_pptx_text(converted, max_chars)
                if text.strip():
                    result.text = text
                    result.page_count = page_count
                    result.method = "libreoffice_pptx"
                    return result
                result.warnings.append("LibreOffice conversion produced empty PPTX text")

            if self.config.enable_com and platform.system() == "Windows":
                converted = self._convert_via_com(path, "pptx", tmp_dir)
                if converted:
                    attempts.append("powerpoint_com_pptx")
                    text, page_count, _truncated = read_pptx_text(converted, max_chars)
                    if text.strip():
                        result.text = text
                        result.page_count = page_count
                        result.method = "powerpoint_com_pptx"
                        return result
                    result.warnings.append("PowerPoint COM conversion produced empty PPTX text")

            ocr_text = self._ocr_via_pdf(path, tmp_dir, max_chars)
            if ocr_text:
                attempts.append("libreoffice_pdf_ocr")
                result.text = ocr_text
                result.method = "libreoffice_pdf_ocr"
                return result

        result.errors.append(
            "Could not extract .ppt text. Tried: "
            + (", ".join(attempts) if attempts else "no methods available")
            + ". Install LibreOffice, Microsoft PowerPoint, or enable OCR."
        )
        return result

    def _find_libreoffice(self) -> str | None:
        return resolve_libreoffice_cmd(self.config.libreoffice_cmd)

    def _convert_via_libreoffice(
        self,
        path: Path,
        target_format: str,
        out_dir: Path,
    ) -> Path | None:
        soffice = self._find_libreoffice()
        if not soffice:
            return None

        try:
            proc = subprocess.run(
                [
                    soffice,
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    target_format,
                    "--outdir",
                    str(out_dir),
                    str(path.resolve()),
                ],
                capture_output=True,
                text=True,
                timeout=self.config.conversion_timeout,
                check=False,
            )
            if proc.returncode != 0:
                logger.debug(
                    "LibreOffice conversion failed (%s): %s",
                    path.name,
                    proc.stderr.strip() or proc.stdout.strip(),
                )
                return None

            converted = out_dir / f"{path.stem}.{target_format}"
            return converted if converted.is_file() else None
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("LibreOffice conversion error for %s: %s", path.name, exc)
            return None

    def _convert_via_com(
        self,
        path: Path,
        target_format: str,
        out_dir: Path,
    ) -> Path | None:
        try:
            import pythoncom
            import win32com.client
        except ImportError:
            return None

        converted = out_dir / f"{path.stem}.{target_format}"
        if converted.exists():
            converted.unlink()

        try:
            pythoncom.CoInitialize()
            if target_format == "docx":
                return self._convert_doc_via_word(path, converted)
            if target_format == "pptx":
                return self._convert_ppt_via_powerpoint(path, converted)
        except Exception as exc:
            logger.debug("COM conversion error for %s: %s", path.name, exc)
            return None
        finally:
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
        return None

    def _convert_doc_via_word(self, path: Path, converted: Path) -> Path | None:
        import win32com.client

        word = None
        document = None
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            document = word.Documents.Open(str(path.resolve()), ReadOnly=True)
            document.SaveAs2(str(converted.resolve()), FileFormat=_COM_DOCX_FORMAT)
            return converted if converted.is_file() else None
        finally:
            if document is not None:
                document.Close(False)
            if word is not None:
                word.Quit()

    def _convert_ppt_via_powerpoint(self, path: Path, converted: Path) -> Path | None:
        import win32com.client

        powerpoint = None
        presentation = None
        try:
            powerpoint = win32com.client.Dispatch("PowerPoint.Application")
            presentation = powerpoint.Presentations.Open(
                str(path.resolve()),
                WithWindow=False,
                ReadOnly=True,
            )
            presentation.SaveAs(str(converted.resolve()), _COM_PPTX_FORMAT)
            return converted if converted.is_file() else None
        finally:
            if presentation is not None:
                presentation.Close()
            if powerpoint is not None:
                powerpoint.Quit()

    def _extract_via_cli_tool(self, path: Path, tool: str) -> str | None:
        binary = shutil.which(tool)
        if not binary:
            return None
        try:
            proc = subprocess.run(
                [binary, str(path.resolve())],
                capture_output=True,
                text=True,
                timeout=self.config.conversion_timeout,
                check=False,
            )
            if proc.returncode == 0:
                return proc.stdout
            logger.debug("%s failed for %s: %s", tool, path.name, proc.stderr.strip())
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("%s error for %s: %s", tool, path.name, exc)
        return None

    def _ocr_via_pdf(self, path: Path, tmp_dir: Path, max_chars: int) -> str | None:
        if not self.ocr or not self.ocr.config.enabled or not self.ocr.is_available():
            return None

        pdf_path = self._convert_via_libreoffice(path, "pdf", tmp_dir)
        if not pdf_path:
            return None

        try:
            ocr_text, _page_count = self.ocr.ocr_pdf(pdf_path)
            text = ocr_text.strip()
            return text[:max_chars] if text else None
        except Exception as exc:
            logger.debug("OCR fallback failed for %s: %s", path.name, exc)
            return None
