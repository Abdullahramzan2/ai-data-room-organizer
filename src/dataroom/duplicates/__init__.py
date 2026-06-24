"""Duplicate file detection (exact hash + near-text similarity)."""

from dataroom.duplicates.config import DuplicateConfig, load_duplicate_config
from dataroom.duplicates.detector import detect_duplicates
from dataroom.duplicates.report import write_duplicate_report_csv
from dataroom.duplicates.review_flags import apply_duplicate_review_flags

__all__ = [
    "DuplicateConfig",
    "apply_duplicate_review_flags",
    "detect_duplicates",
    "load_duplicate_config",
    "write_duplicate_report_csv",
]
