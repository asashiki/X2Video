"""Fetch stage: source → Hard Filter → Ledger → candidates.json."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from x2video.config.schema import X2VideoConfig
from x2video.pipeline.hard_filter import apply_hard_filter, is_fresh
from x2video.pipeline.io import write_candidates
from x2video.pipeline.ledger import Ledger
from x2video.pipeline.workdir import resolve_run_dir
from x2video.source.factory import create_source
from x2video.source.models import CandidateTweet


def choose_fetch_pool(
    raw: list[CandidateTweet],
    ledger: Ledger,
    *,
    skip_ledger: bool = False,
) -> list[CandidateTweet]:
    """Keep new posts first. If everything was already fetched, reuse unpicked ones.

    Already-made Picks stay excluded so the same digest is not rebuilt.
    """
    not_picked = [c for c in raw if not ledger.is_pick(c.id)]
    if skip_ledger:
        return not_picked
    unseen = [c for c in not_picked if not ledger.is_seen(c.id)]
    return unseen or not_picked


def run_fetch(
    cfg: X2VideoConfig,
    *,
    keywords: list[str] | None = None,
    max_results: int | None = None,
    skip_hard_filter: bool = False,
    skip_ledger: bool = False,
    date: str | None = None,
    output: Path | None = None,
) -> dict[str, Any]:
    kw = list(keywords) if keywords else list(cfg.domain_keywords)
    if not kw:
        raise ValueError("No domain keywords configured.")

    limit = max_results if max_results is not None else cfg.curation.max_candidates
    hf = cfg.hard_filter
    ledger = Ledger.load(cfg.work_dir)

    source_cfg = cfg.model_copy(deep=True)
    if skip_hard_filter:
        source_cfg.hard_filter.min_likes = 0
        source_cfg.hard_filter.min_retweets = 0
        source_cfg.hard_filter.min_replies = 0
        source_cfg.hard_filter.views_threshold = 0
    source = create_source(source_cfg)

    raw = source.fetch(
        kw,
        time_window_hours=hf.time_window_hours,
        max_results=max(limit * 2, limit),
    )
    if not raw:
        raise RuntimeError("X 搜索没有返回帖子。到「设置与诊断」看数据源是否已登录。")

    pool = choose_fetch_pool(raw, ledger, skip_ledger=skip_ledger)

    filtered: list[CandidateTweet]
    if skip_hard_filter:
        filtered = [c for c in pool if is_fresh(c, hf.max_age_hours)]
    else:
        filtered = apply_hard_filter(pool, hf)

    filtered.sort(key=lambda c: c.engagement_score(), reverse=True)
    filtered = filtered[:limit]
    if not filtered:
        raise RuntimeError(
            f"搜到 {len(raw)} 条，去重后 {len(pool)} 条，互动门槛筛完 0 条。今天可能没有够热的新帖。"
        )

    ledger.mark_seen(c.id for c in raw)
    ledger.save()

    run_dir = resolve_run_dir(cfg.work_dir, date)
    dest = output or (run_dir / "candidates.json")
    meta = {
        "provider": source.name,
        "keywords": kw,
        "time_window_hours": hf.time_window_hours,
        "fetched": len(raw),
        "after_ledger": len(pool),
        "kept": len(filtered),
        "skip_hard_filter": skip_hard_filter,
        "skip_ledger": skip_ledger,
    }
    write_candidates(dest, filtered, meta=meta)
    return {"output": dest, "ledger": ledger.path, **meta, "candidates": filtered}
