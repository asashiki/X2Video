"""Dated work directories: work/YYYY-MM-DD/."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def today_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def resolve_run_dir(work_dir: str | Path, date: str | None = None) -> Path:
    """Return work/YYYY-MM-DD/, creating it if needed."""
    day = date or today_stamp()
    path = Path(work_dir) / day
    path.mkdir(parents=True, exist_ok=True)
    return path


def timestamp_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")
