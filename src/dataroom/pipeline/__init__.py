"""Pipeline orchestration."""

from __future__ import annotations

__all__ = ["run_pipeline", "run_rerun"]


def __getattr__(name: str):
    if name == "run_pipeline":
        from dataroom.pipeline.run import run_pipeline

        return run_pipeline
    if name == "run_rerun":
        from dataroom.pipeline.rerun import run_rerun

        return run_rerun
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
