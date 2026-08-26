"""End-to-end run + resume from a dated work directory."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from x2video.config.schema import X2VideoConfig
from x2video.pipeline.card import run_card
from x2video.pipeline.curate import run_curate
from x2video.pipeline.fetch import run_fetch
from x2video.pipeline.render import run_render
from x2video.pipeline.script import run_script
from x2video.pipeline.workdir import resolve_run_dir

STAGES = ("fetch", "curate", "card", "script", "render")


def _has_output(run_dir: Path, stage: str) -> bool:
    if stage == "fetch":
        return (run_dir / "candidates.json").exists()
    if stage == "curate":
        return (run_dir / "picks.json").exists()
    if stage == "card":
        cards = run_dir / "cards"
        return cards.exists() and any(cards.glob("*.png"))
    if stage == "script":
        return (run_dir / "script.json").exists()
    if stage == "render":
        return (run_dir / "publish_kit.json").exists()
    return False


def _run_async(coro):
    return asyncio.run(coro)


def run_pipeline(
    cfg: X2VideoConfig,
    *,
    date: str | None = None,
    auto: bool = True,
    from_stage: str = "fetch",
    force: bool = False,
    keywords: list[str] | None = None,
    skip_hard_filter: bool = False,
    skip_ledger: bool = False,
    pick_indices: list[int] | None = None,
    on_stage: Callable[[str, str], None] | None = None,
) -> dict[str, Any]:
    if from_stage not in STAGES:
        raise ValueError(f"Unknown stage '{from_stage}'. Use one of: {', '.join(STAGES)}")

    run_dir = resolve_run_dir(cfg.work_dir, date)
    start = STAGES.index(from_stage)
    results: dict[str, Any] = {"run_dir": str(run_dir), "stages": {}}

    def should_run(stage: str) -> bool:
        idx = STAGES.index(stage)
        if idx < start:
            return False
        if force:
            return True
        return not _has_output(run_dir, stage)

    def note(stage: str, status: str) -> None:
        if on_stage:
            on_stage(stage, status)

    if should_run("fetch"):
        note("fetch", "start")
        results["stages"]["fetch"] = run_fetch(
            cfg,
            keywords=keywords,
            skip_hard_filter=skip_hard_filter,
            skip_ledger=skip_ledger,
            date=date,
        )
        note("fetch", "done")
    else:
        note("fetch", "skip")
        results["stages"]["fetch"] = {"skipped": True}

    if should_run("curate"):
        note("curate", "start")
        results["stages"]["curate"] = _run_async(
            run_curate(cfg, date=date, auto=auto, indices=pick_indices)
        )
        note("curate", "done")
    else:
        note("curate", "skip")
        results["stages"]["curate"] = {"skipped": True}

    if should_run("card"):
        note("card", "start")
        results["stages"]["card"] = run_card(cfg, date=date)
        note("card", "done")
    else:
        note("card", "skip")
        results["stages"]["card"] = {"skipped": True}

    if should_run("script"):
        note("script", "start")
        results["stages"]["script"] = _run_async(run_script(cfg, date=date))
        note("script", "done")
    else:
        note("script", "skip")
        results["stages"]["script"] = {"skipped": True}

    if should_run("render"):
        note("render", "start")
        results["stages"]["render"] = _run_async(run_render(cfg, date=date))
        note("render", "done")
    else:
        note("render", "skip")
        results["stages"]["render"] = {"skipped": True}

    return results
