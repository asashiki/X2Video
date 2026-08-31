"""Small shared helpers (JSON extraction, formatting)."""

from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CST = timezone(timedelta(hours=8))


def discover_browser_executable() -> Path | None:
    """Locate Chromium without requiring it to be on PATH."""
    configured = os.environ.get("X2VIDEO_BROWSER_EXECUTABLE")
    if configured:
        path = Path(configured)
        return path if path.exists() else None
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome", "msedge"):
        found = shutil.which(name)
        if found and Path(found).exists():
            return Path(found)
    patterns = (
        "chromium-*/chrome-win64/chrome.exe",
        "chromium-*/chrome-linux/chrome",
        "chromium-*/chrome-linux64/chrome",
        "chromium-*/chrome-mac/Chromium",
        "chromium-*/chrome-mac-arm64/Chromium",
    )
    roots: list[Path] = []
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        roots.append(Path(local_app) / "ms-playwright")
    roots.extend(
        [
            Path.home() / "AppData" / "Local" / "ms-playwright",
            Path.home() / ".cache" / "ms-playwright",
            Path.home() / "Library" / "Caches" / "ms-playwright",
        ]
    )
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            matches = sorted(root.glob(pattern))
            if matches:
                return matches[-1]
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            exe = Path(playwright.chromium.executable_path)
        return exe if exe.exists() else None
    except Exception:
        return None


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


_GOAL_STOP = {
    "帮我",
    "做一条",
    "做成",
    "一条",
    "今日",
    "今天",
    "中文",
    "口播",
    "热帖",
    "热点",
    "速览",
    "视频",
    "外文",
    "抓取",
    "最近",
}


def search_terms(query: str, fallback: list[str] | None = None) -> list[str]:
    """Turn the Studio goal into fetch keywords, keeping config terms as backup."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        value = (term or "").strip()
        key = value.lower()
        if len(value) < 2 or key in seen or value in _GOAL_STOP:
            return
        seen.add(key)
        terms.append(value)

    text = (query or "").strip()
    for match in re.findall(r"[“\"']([^”\"']+)[”\"']", text):
        add(match)
    cleaned = text
    for stop in sorted(_GOAL_STOP, key=len, reverse=True):
        cleaned = cleaned.replace(stop, " ")
    for match in re.findall(r"[A-Za-z][A-Za-z0-9+\-]{1,20}", cleaned or text):
        add(match)
    for match in re.findall(r"[\u4e00-\u9fff]{2,8}", cleaned):
        add(match)
    for item in fallback or []:
        add(item)
    return terms[:12] or list(fallback or [])


def picks_for_duration(seconds: int, configured: int = 6) -> int:
    """How many digest items to aim for given a target length."""
    target = max(20, int(seconds or 60))
    needed = max(2, round(target / 16))
    return max(2, min(int(configured or 6), needed))


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


_DATE_LEAD_RE = re.compile(
    r"^(今天|昨天|前天|\d{1,2}月\d{1,2}[日号])[，,、]?\s*"
)


def strip_date_lead(narration: str) -> str:
    """Drop a leading 几月几号 / 今天 so the date is not chanted twice."""
    return _DATE_LEAD_RE.sub("", (narration or "").strip(), count=1).strip()


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
    if _DATE_LEAD_RE.match(text):
        return text
    return f"{label}，{text}"


def is_same_day_digest(picks: list[Any]) -> bool:
    """True when every Pick falls on the same China-local calendar day."""
    labels = {
        format_md_date(getattr(pick, "created_at", "") or "")
        for pick in picks
        if getattr(pick, "created_at", None)
    }
    return len(labels) <= 1


_PUNCT_ONLY = re.compile(r"^[。！？!?；;，,、.\s]+$")


def split_subtitles(text: str, *, max_len: int = 48) -> list[str]:
    """Split narration into spoken units. Keep sentences intact.

    Each returned line is sent to TTS as one clip. Do not slice on a
    character budget — that pauses mid-word. Break on sentence
    punctuation, and only on a comma if a sentence is unusually long.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = [part.strip() for part in re.split(r"(?<=[。！？!?])", text) if part.strip()]
    lines: list[str] = []
    for sentence in sentences:
        if _PUNCT_ONLY.match(sentence):
            if lines:
                lines[-1] += sentence.strip()
            continue
        if len(sentence) <= max_len:
            lines.append(sentence)
            continue
        buf = ""
        for clause in re.split(r"(?<=[，,、；;])", sentence):
            piece = clause.strip()
            if not piece:
                continue
            if buf and len(buf) + len(piece) > max_len:
                lines.append(buf)
                buf = piece
            else:
                buf += piece
        if buf:
            lines.append(buf)
    return lines or [text]
