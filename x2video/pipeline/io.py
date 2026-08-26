"""Read/write pipeline artifacts in a run directory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from x2video.pipeline.models import DigestScript, Pick
from x2video.source.models import CandidateTweet


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        data = payload.model_dump()
    else:
        data = payload
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_candidates(path: Path) -> tuple[dict[str, Any], list[CandidateTweet]]:
    raw = read_json(path)
    items = raw.get("candidates") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return (raw if isinstance(raw, dict) else {}), []
    candidates = [CandidateTweet.model_validate(item) for item in items if isinstance(item, dict)]
    meta = raw if isinstance(raw, dict) else {}
    return meta, candidates


def write_candidates(
    path: Path,
    candidates: list[CandidateTweet],
    *,
    meta: dict[str, Any] | None = None,
) -> Path:
    payload = dict(meta or {})
    payload["candidates"] = [c.model_dump() for c in candidates]
    payload["kept"] = len(candidates)
    return write_json(path, payload)


def load_picks(path: Path) -> tuple[dict[str, Any], list[Pick]]:
    raw = read_json(path)
    items = raw.get("picks") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return (raw if isinstance(raw, dict) else {}), []
    picks = [Pick.model_validate(item) for item in items if isinstance(item, dict)]
    meta = raw if isinstance(raw, dict) else {}
    return meta, picks


def write_picks(path: Path, picks: list[Pick], *, meta: dict[str, Any] | None = None) -> Path:
    payload = dict(meta or {})
    payload["picks"] = [p.model_dump() for p in picks]
    payload["count"] = len(picks)
    return write_json(path, payload)


def load_script(path: Path) -> DigestScript:
    return DigestScript.model_validate(read_json(path))


def write_script(path: Path, script: DigestScript) -> Path:
    return write_json(path, script)
