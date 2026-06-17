"""Classification mode helpers."""

from __future__ import annotations

from dataroom.settings import Settings


def tier3_enabled(settings: Settings) -> bool:
    """True when Tier 3 reasoning provider escalation is permitted."""
    return settings.classification_mode in {"hybrid", "api"}
