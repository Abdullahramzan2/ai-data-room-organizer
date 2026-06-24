"""Environment health checks for the data room organizer."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from dataroom.doctor.models import DoctorReport
    from dataroom.settings import Settings

__all__ = ["run_doctor"]


def run_doctor(
    config_path: Path | None = None,
    *,
    settings: Settings | None = None,
) -> DoctorReport:
    from dataroom.doctor.checks import run_doctor as _run_doctor

    return _run_doctor(config_path, settings=settings)
