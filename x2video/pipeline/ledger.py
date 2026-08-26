"""Ledger: persistent record of seen tweet IDs and completed Picks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Ledger:
    """On-disk ledger at ``work/ledger.json``.

    * ``seen`` — tweet IDs already pulled by fetch (skip next day)
    * ``picks`` — tweet IDs already turned into a digest Pick
    """

    def __init__(self, path: Path, data: dict[str, Any] | None = None) -> None:
        self.path = path
        payload = data or {}
        seen = payload.get("seen") or {}
        picks = payload.get("picks") or {}
        # Allow a bare list of ids from older drafts
        if isinstance(seen, list):
            seen = {str(i): {} for i in seen}
        if isinstance(picks, list):
            picks = {str(i): {} for i in picks}
        self.seen: dict[str, dict[str, Any]] = {str(k): dict(v) for k, v in seen.items()}
        self.picks: dict[str, dict[str, Any]] = {str(k): dict(v) for k, v in picks.items()}

    @classmethod
    def load(cls, work_dir: str | Path) -> Ledger:
        path = Path(work_dir) / "ledger.json"
        if not path.exists():
            return cls(path)
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(path)
        if not isinstance(raw, dict):
            return cls(path)
        return cls(path, raw)

    def is_seen(self, tweet_id: str) -> bool:
        return str(tweet_id) in self.seen

    def is_pick(self, tweet_id: str) -> bool:
        return str(tweet_id) in self.picks

    def mark_seen(self, tweet_ids: Iterable[str], *, extra: dict[str, Any] | None = None) -> None:
        for tweet_id in tweet_ids:
            tid = str(tweet_id)
            record = dict(self.seen.get(tid) or {})
            record.setdefault("first_seen", _now_iso())
            record["last_seen"] = _now_iso()
            if extra:
                record.update(extra)
            self.seen[tid] = record

    def mark_picks(self, tweet_ids: Iterable[str], *, extra: dict[str, Any] | None = None) -> None:
        for tweet_id in tweet_ids:
            tid = str(tweet_id)
            record = dict(self.picks.get(tid) or {})
            record.setdefault("picked_at", _now_iso())
            if extra:
                record.update(extra)
            self.picks[tid] = record
            if tid not in self.seen:
                self.mark_seen([tid])

    def save(self) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "seen": self.seen,
            "picks": self.picks,
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return self.path
