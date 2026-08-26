"""Small shared helpers (JSON extraction, formatting)."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any


def strip_json_fence(text: str) -> str:
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*([\s\S]*?)\s*```$", text)
    if fence:
        return fence.group(1).strip()
    return text


def parse_json_payload(text: str) -> Any:
    """Parse JSON from a model response, tolerating fences and surrounding prose."""
    cleaned = strip_json_fence(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_obj = cleaned.find("{")
        start_arr = cleaned.find("[")
        candidates = [i for i in (start_obj, start_arr) if i >= 0]
        if not candidates:
            raise
        start = min(candidates)
        end_obj = cleaned.rfind("}")
        end_arr = cleaned.rfind("]")
        end = max(end_obj, end_arr)
        if end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def format_count(n: int) -> str:
    """X-style compact count (1.2K / 3.4M)."""
    if n >= 1_000_000:
        value = n / 1_000_000
        return f"{value:.1f}M".replace(".0M", "M")
    if n >= 1_000:
        value = n / 1_000
        return f"{value:.1f}K".replace(".0K", "K")
    return str(int(n))


def format_tweet_time(iso: str) -> str:
    if not iso:
        return ""
    raw = iso.strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso[:16]


def split_subtitles(text: str, *, max_len: int = 22) -> list[str]:
    """Split narration into subtitle lines by punctuation, then length."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])", text)
    lines: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        while len(chunk) > max_len:
            lines.append(chunk[:max_len])
            chunk = chunk[max_len:]
        if chunk:
            lines.append(chunk)
    return lines or [text]
