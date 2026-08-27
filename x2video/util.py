"""Small shared helpers (JSON extraction, formatting)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

CST = timezone(timedelta(hours=8))


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


def parse_tweet_datetime(iso: str) -> datetime | None:
    """Parse a tweet timestamp into China local time."""
    if not iso:
        return None
    raw = iso.strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(CST)
    except ValueError:
        return None


def format_tweet_time(iso: str) -> str:
    dt = parse_tweet_datetime(iso)
    if dt is None:
        return iso[:16] if iso else ""
    return dt.strftime("%Y-%m-%d %H:%M")


def format_md_date(iso: str = "", *, fallback: datetime | None = None) -> str:
    """News-desk date: 8月27日. Always China local time."""
    dt = parse_tweet_datetime(iso) if iso else None
    if dt is None:
        dt = fallback or datetime.now(CST)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=CST)
        else:
            dt = dt.astimezone(CST)
    return f"{dt.month}月{dt.day}日"


def tweet_age_hours(iso: str, *, now: datetime | None = None) -> float | None:
    dt = parse_tweet_datetime(iso)
    if dt is None:
        return None
    current = now or datetime.now(CST)
    if current.tzinfo is None:
        current = current.replace(tzinfo=CST)
    else:
        current = current.astimezone(CST)
    return (current - dt).total_seconds() / 3600.0


def punchline(text: str, *, limit: int = 14) -> str:
    """Short on-screen 花字 (8–16 字). Prefer the Chinese-heavy clause."""
    clauses = [p.strip() for p in re.split(r"[，。！？!?]", text or "") if p.strip()]

    def _score(clause: str) -> tuple[int, int]:
        cjk = sum(1 for ch in clause if "\u4e00" <= ch <= "\u9fff")
        latin = sum(1 for ch in clause if ch.isascii() and ch.isalpha())
        return (cjk, -latin)

    viable = [c for c in clauses if _score(c)[0] >= 4]
    pure = [c for c in viable if _score(c)[1] == 0]
    if pure:
        chosen = pure[0]
    elif viable:
        chosen = max(viable, key=_score)
    else:
        chosen = re.sub(r"\s+", "", text or "")
    return (chosen[:limit].strip() or "外网热帖")


def ensure_date_lead(narration: str, date_label: str) -> str:
    """Guarantee a news-desk date at the start of a spoken line."""
    text = (narration or "").strip()
    label = (date_label or "").strip()
    if not text:
        return label
    if not label:
        return text
    if label in text[:18]:
        return text
    if re.match(r"^(今天|昨天|前天|\d{1,2}月\d{1,2}日)", text):
        return text
    return f"{label}，{text}"


_PUNCT_ONLY = re.compile(r"^[。！？!?；;，,、.\s]+$")


def split_subtitles(text: str, *, max_len: int = 18) -> list[str]:
    """Split narration into subtitle lines by punctuation, then length.

    These lines are both what TTS speaks (one clip per line) and what
    appears on screen, so they must be the same string the voice reads.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;])", text)
    lines: list[str] = []
    for part in parts:
        chunk = part.strip()
        if not chunk:
            continue
        if len(chunk) > max_len:
            clauses = re.split(r"(?<=[，,、])", chunk)
            buf = ""
            for clause in clauses:
                piece = clause.strip()
                if not piece:
                    continue
                if buf and len(buf) + len(piece) > max_len:
                    lines.append(buf)
                    buf = piece
                else:
                    buf += piece
            if buf:
                chunk = buf
            else:
                continue
        while len(chunk) > max_len:
            rest = chunk[max_len:]
            if _PUNCT_ONLY.match(rest):
                lines.append(chunk)
                chunk = ""
                break
            lines.append(chunk[:max_len])
            chunk = rest
        if chunk:
            lines.append(chunk)
    cleaned: list[str] = []
    for line in lines:
        if _PUNCT_ONLY.match(line):
            if cleaned:
                cleaned[-1] += line.strip()
            continue
        cleaned.append(line)
    return cleaned or [text]
