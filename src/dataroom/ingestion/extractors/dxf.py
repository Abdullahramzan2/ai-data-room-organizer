"""DXF CAD text and layer extractor."""

from __future__ import annotations

from pathlib import Path

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.models import ExtractedDocument, ExtractionMethod, FileMetadata


def extract_dxf_text(path: Path, *, max_chars: int) -> tuple[str, list[str], str]:
    try:
        import ezdxf
    except ImportError:
        return "", [], "failed: ezdxf not installed"

    lines: list[str] = []
    signals: list[str] = []

    try:
        from ezdxf.filemanagement import readfile

        doc = readfile(str(path))
    except Exception as exc:
        return "", [], f"failed: {exc}"

    msp = doc.modelspace()
    layers = sorted({layer.dxf.name for layer in doc.layers if layer.dxf.name})
    if layers:
        layer_summary = ", ".join(layers[:40])
        lines.append(f"Layers: {layer_summary}")
        signals.append(f"layers:{layer_summary[:120]}")

    text_entities = 0
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype in {"TEXT", "MTEXT", "ATTRIB", "ATTDEF"}:
            raw = getattr(entity.dxf, "text", "") or ""
            text = str(raw).strip()
            if text:
                text_entities += 1
                layer = getattr(entity.dxf, "layer", "")
                prefix = f"[{layer}] " if layer else ""
                lines.append(f"{prefix}{text[:300]}")
                signals.append(f"text:{text[:80]}")
        elif dxftype == "INSERT" and hasattr(entity.dxf, "name"):
            block_name = str(entity.dxf.name).strip()
            if block_name:
                lines.append(f"Block: {block_name}")
                signals.append(f"block:{block_name}")

    if text_entities:
        lines.insert(0, f"CAD text entities: {text_entities}")

    text = "\n".join(lines).strip()
    if not text:
        return "", signals, "partial"
    if len(text) > max_chars:
        text = text[:max_chars]
    return text, signals, "success"


class DxfExtractor(BaseExtractor):
    extensions = {".dxf"}

    def extract(self, path: Path, metadata: FileMetadata) -> ExtractedDocument:
        doc = ExtractedDocument(metadata=metadata, extraction_method=ExtractionMethod.NATIVE)
        doc.extra["file_type_handler"] = "dxf_parser"

        text, signals, status = extract_dxf_text(path, max_chars=self.max_text_chars)
        doc.extra["parse_status"] = status
        doc.extra["extracted_cad_signals"] = signals

        if text:
            doc.text_content = text
        elif status == "failed: ezdxf not installed":
            doc.warnings.append("Install ezdxf for DXF text extraction (pip install ezdxf)")
            doc.extraction_method = ExtractionMethod.FAILED
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            doc.extra["parse_status"] = "partial"
        else:
            doc.extraction_method = ExtractionMethod.FAILED
            doc.warnings.append("DXF contained no extractable text — filename fallback")
            doc.text_content = metadata.file_name.replace("_", " ").replace("-", " ")
            doc.extra["parse_status"] = "partial"

        return doc
