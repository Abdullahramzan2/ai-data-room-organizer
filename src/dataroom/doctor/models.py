"""Data models for doctor health-check results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CheckStatus = Literal["pass", "warn", "fail", "skip"]


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "fix": self.fix,
        }


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(check.status == "fail" for check in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "checks": [check.to_dict() for check in self.checks],
            "has_failures": self.has_failures,
        }
