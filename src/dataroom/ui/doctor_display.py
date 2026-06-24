"""Streamlit display for doctor environment checks."""

from __future__ import annotations

from collections import Counter

import pandas as pd
import streamlit as st

from dataroom.doctor.models import CheckResult, DoctorReport

_STATUS_LABELS = {
    "pass": "Pass",
    "warn": "Warn",
    "fail": "Fail",
    "skip": "Skip",
}


def _check_label(name: str) -> str:
    if name.startswith("package:"):
        return name.split(":", 1)[1]
    return name.replace("_", " ").title()


def _doctor_table_rows(checks: list[CheckResult]) -> list[dict[str, str]]:
    return [
        {
            "Status": _STATUS_LABELS.get(check.status, check.status),
            "Check": _check_label(check.name),
            "Message": check.message,
        }
        for check in checks
    ]


def display_doctor_report(report: DoctorReport) -> None:
    """Render doctor results as metrics, a table, and optional fix hints."""
    checks = report.checks
    counts = Counter(check.status for check in checks)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Passed", counts.get("pass", 0))
    c2.metric("Warnings", counts.get("warn", 0))
    c3.metric("Failed", counts.get("fail", 0))
    c4.metric("Skipped", counts.get("skip", 0))

    rows = _doctor_table_rows(checks)
    st.dataframe(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        height=min(420, 38 + len(rows) * 35),
    )

    fixes = [
        (check.name, check.fix)
        for check in checks
        if check.fix and check.status in {"warn", "fail"}
    ]
    if fixes:
        st.subheader("Suggested fixes")
        for name, fix in fixes:
            st.markdown(f"**{_check_label(name)}** — {fix}")
