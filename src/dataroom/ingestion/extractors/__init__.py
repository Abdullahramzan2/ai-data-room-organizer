"""File-type-specific text extractors."""

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.email import EmlExtractor, MsgExtractor
from dataroom.ingestion.extractors.image import ImageExtractor
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig, LegacyOfficeConverter
from dataroom.ingestion.extractors.office import (
    DocExtractor,
    DocxExtractor,
    PptExtractor,
    PptxExtractor,
    XlsExtractor,
    XlsxExtractor,
)
from dataroom.ingestion.extractors.pdf import PdfExtractor
from dataroom.ingestion.extractors.text import TextExtractor

__all__ = ["BaseExtractor", "LegacyOfficeConfig", "build_extractors"]


def build_extractors(
    ocr=None,
    max_text_chars: int = 500_000,
    legacy_office_config: LegacyOfficeConfig | None = None,
) -> list[BaseExtractor]:
    """Instantiate all supported extractors."""
    common = {"ocr": ocr, "max_text_chars": max_text_chars}
    legacy = LegacyOfficeConverter(config=legacy_office_config, ocr=ocr)
    return [
        PdfExtractor(**common),
        DocxExtractor(**common),
        DocExtractor(**common, legacy=legacy),
        XlsxExtractor(**common),
        XlsExtractor(**common),
        PptxExtractor(**common),
        PptExtractor(**common, legacy=legacy),
        ImageExtractor(**common),
        TextExtractor(**common),
        EmlExtractor(**common),
        MsgExtractor(**common),
    ]
