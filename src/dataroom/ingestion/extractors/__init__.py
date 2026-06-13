"""File-type-specific text extractors."""

from dataroom.ingestion.extractors.base import BaseExtractor
from dataroom.ingestion.extractors.factory import build_extractors
from dataroom.ingestion.extractors.legacy_office import LegacyOfficeConfig

__all__ = ["BaseExtractor", "LegacyOfficeConfig", "build_extractors"]
