"""Duplicate file detection (exact hash + near-text similarity)."""

from dataroom.duplicates.config import DuplicateConfig, load_duplicate_config
from dataroom.duplicates.detector import detect_duplicates
from dataroom.duplicates.report import write_duplicate_report_csv

__all__ = [
    "DuplicateConfig",
    "detect_duplicates",
    "load_duplicate_config",
    "write_duplicate_report_csv",
]
