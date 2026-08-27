"""Unattended QC for a Publish Kit. Fail loud; warn on thin digests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip().splitlines()[0].strip())


def inspect_kit(
    *,
    video: Path,
    cover: Path,
    pick_count: int,
    min_picks: int = 3,
    min_seconds: float = 8.0,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if not video.exists() or video.stat().st_size < 10_000:
        errors.append(f"video missing or too small: {video}")
    else:
        try:
            duration = _duration(video)
        except Exception as exc:
            errors.append(f"ffprobe failed: {exc}")
            duration = 0.0
        if duration < min_seconds:
            errors.append(f"video too short: {duration:.1f}s")
    if not cover.exists() or cover.stat().st_size < 5_000:
        errors.append(f"cover missing: {cover}")
    if pick_count <= 0:
        errors.append("no picks in this digest")
    elif pick_count < min_picks:
        warnings.append(
            f"only {pick_count} pick(s); digest will be short. "
            "Relax keywords/hard_filter or wait for a denser day."
        )

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "pick_count": pick_count,
        "video": str(video),
        "cover": str(cover),
    }
