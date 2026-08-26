"""Curation stage: LLM scoring → candidates.md → picks.json (Gate 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.llm.base import LLMProvider
from x2video.llm.client import create_llm_provider
from x2video.pipeline.io import load_candidates, write_json, write_picks
from x2video.pipeline.ledger import Ledger
from x2video.pipeline.models import Pick
from x2video.pipeline.prompts import load_prompt
from x2video.pipeline.workdir import resolve_run_dir
from x2video.source.models import CandidateTweet
from x2video.util import format_count, parse_json_payload

CURATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "score": {"type": "number"},
                    "reason": {"type": "string"},
                    "translation": {"type": "string"},
                    "reject": {"type": "boolean"},
                },
                "required": ["id", "score", "reason", "translation", "reject"],
            },
        }
    },
    "required": ["items"],
}

MIN_KEEP_SCORE = 6.0


def _candidate_payload(c: CandidateTweet) -> dict[str, Any]:
    return {
        "id": c.id,
        "text": c.text,
        "author_name": c.author_name,
        "author_username": c.author_username,
        "likes": c.likes,
        "retweets": c.retweets,
        "replies": c.replies,
        "views": c.views,
        "url": c.url,
        "created_at": c.created_at,
        "has_media": bool(c.media_urls),
    }


def _parse_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        items = raw.get("items") or raw.get("candidates") or raw.get("picks")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


async def score_candidates(
    candidates: list[CandidateTweet],
    *,
    llm: LLMProvider,
    exclude_pick_ids: list[str],
    top_n: int,
) -> list[Pick]:
    if not candidates:
        return []
    system = load_prompt("curation-prompt.md")
    user = (
        "Score these candidates for a Chinese AI/tech short-video digest.\n"
        f"Need up to {top_n} keepers. Exclude ids already used as Picks: "
        f"{exclude_pick_ids or []}\n\n"
        f"{_json_dumps({'candidates': [_candidate_payload(c) for c in candidates]})}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    try:
        parsed = await llm.complete_structured(messages, CURATION_SCHEMA)
    except Exception:
        text = await llm.complete(messages)
        parsed = parse_json_payload(text)

    by_id = {c.id: c for c in candidates}
    scored: list[Pick] = []
    seen: set[str] = set()
    for item in _parse_items(parsed):
        tid = str(item.get("id") or "").strip()
        if not tid or tid not in by_id or tid in seen:
            continue
        seen.add(tid)
        base = by_id[tid]
        reject = bool(item.get("reject"))
        try:
            score = float(item.get("score") or 0)
        except (TypeError, ValueError):
            score = 0.0
        pick = Pick(
            **base.model_dump(),
            translation=str(item.get("translation") or "").strip(),
            score=score,
            reason=str(item.get("reason") or "").strip(),
        )
        if reject or score < MIN_KEEP_SCORE:
            continue
        if tid in exclude_pick_ids:
            continue
        scored.append(pick)
    scored.sort(key=lambda p: p.score, reverse=True)
    return scored


def render_candidates_md(scored: list[Pick], *, date: str, kept_ids: set[str]) -> str:
    lines = [
        f"# Candidates {date}",
        "",
        "勾选 Pick：把要做的条目编号留给 Gate 1，或使用 `--auto` 按分数取前 N。",
        "",
    ]
    if not scored:
        lines.append("_No candidates scored above threshold._")
        return "\n".join(lines) + "\n"
    for i, p in enumerate(scored, start=1):
        mark = "✓ Pick" if p.id in kept_ids else ""
        lines.extend(
            [
                f"## {i}. {p.score:.1f} @{p.author_username or 'unknown'} {mark}",
                "",
                f"- 作者: {p.author_name} (@{p.author_username})",
                f"- 互动: {format_count(p.likes)} likes / {format_count(p.retweets)} RT / "
                f"{format_count(p.replies)} replies / {format_count(p.views)} views",
                f"- 链接: {p.url}",
                f"- 理由: {p.reason}",
                "",
                "原文:",
                "",
                f"> {p.text.replace(chr(10), chr(10) + '> ')}",
                "",
                "翻译:",
                "",
                f"> {p.translation}",
                "",
            ]
        )
    return "\n".join(lines)


def select_picks(scored: list[Pick], *, top_n: int, indices: list[int] | None) -> list[Pick]:
    if indices:
        out: list[Pick] = []
        for i in indices:
            if 1 <= i <= len(scored):
                out.append(scored[i - 1])
        return out
    return scored[:top_n]


async def run_curate(
    cfg: X2VideoConfig,
    *,
    date: str | None = None,
    input_path: Path | None = None,
    output_path: Path | None = None,
    auto: bool = True,
    indices: list[int] | None = None,
    llm: LLMProvider | None = None,
) -> dict[str, Any]:
    run_dir = resolve_run_dir(cfg.work_dir, date)
    src = input_path or (run_dir / "candidates.json")
    if not src.exists():
        raise FileNotFoundError(f"Candidates file not found: {src}. Run `x2video fetch` first.")

    _meta, candidates = load_candidates(src)
    ledger = Ledger.load(cfg.work_dir)
    exclude = list(ledger.picks.keys())

    owns_llm = llm is None
    llm = llm or create_llm_provider(cfg.llm)
    try:
        scored = await score_candidates(
            candidates,
            llm=llm,
            exclude_pick_ids=exclude,
            top_n=cfg.curation.top_n,
        )
    finally:
        if owns_llm:
            await llm.close()

    picks = select_picks(scored, top_n=cfg.curation.top_n, indices=indices)
    day = run_dir.name
    md = render_candidates_md(scored, date=day, kept_ids={p.id for p in picks})
    md_path = run_dir / "candidates.md"
    md_path.write_text(md, encoding="utf-8")

    dest = output_path or (run_dir / "picks.json")
    write_picks(
        dest,
        picks,
        meta={
            "date": day,
            "auto": auto,
            "scored": len(scored),
            "top_n": cfg.curation.top_n,
        },
    )
    write_json(run_dir / "scored.json", {"items": [p.model_dump() for p in scored]})

    if picks:
        ledger.mark_picks((p.id for p in picks), extra={"date": day})
        ledger.save()

    return {
        "input": src,
        "output": dest,
        "markdown": md_path,
        "scored": scored,
        "picks": picks,
    }


def _json_dumps(payload: Any) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
