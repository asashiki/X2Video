"""Score and select picks via LLM curation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from x2video.cli.common import die, parse_indices, run_async
from x2video.llm.client import create_llm_provider
from x2video.pipeline.curate import (
    render_candidates_md,
    score_candidates,
    select_picks,
)
from x2video.pipeline.io import load_candidates, write_json, write_picks
from x2video.pipeline.ledger import Ledger
from x2video.pipeline.workdir import resolve_run_dir
from x2video.util import format_count

app = typer.Typer(help="Score candidates via LLM curation and select picks")
console = Console()


@app.callback(invoke_without_command=True)
def curate(
    ctx: typer.Context,
    candidates: Path | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to candidates JSON from fetch",
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Output path for selected picks"
    ),
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
    auto: bool | None = typer.Option(
        None, "--auto/--no-auto", help="Override blocking mode from config"
    ),
) -> None:
    """Score candidates via LLM curation and produce a ranked pick list."""
    cfg = ctx.obj
    blocking = cfg.curation.blocking_mode if auto is None else (not auto)
    run_dir = resolve_run_dir(cfg.work_dir, date)
    src = candidates or (run_dir / "candidates.json")
    dest = output or (run_dir / "picks.json")
    try:
        _meta, items = load_candidates(src)
    except FileNotFoundError:
        die(f"Candidates file not found: {src}. Run `x2video fetch` first.")

    ledger = Ledger.load(cfg.work_dir)

    async def _score():
        llm = create_llm_provider(cfg.llm)
        try:
            return await score_candidates(
                items,
                llm=llm,
                exclude_pick_ids=list(ledger.picks.keys()),
                top_n=cfg.curation.top_n,
            )
        finally:
            await llm.close()

    try:
        scored = run_async(_score())
    except Exception as exc:
        die(f"curate failed: {exc}")

    if not scored:
        die("No candidates passed curation. Try --skip-hard-filter on fetch or relax keywords.")

    table = Table(title="Curation")
    table.add_column("#", justify="right")
    table.add_column("score", justify="right")
    table.add_column("author")
    table.add_column("likes", justify="right")
    table.add_column("text")
    for i, p in enumerate(scored, start=1):
        snippet = (p.text or "").replace("\n", " ")[:60]
        table.add_row(
            str(i),
            f"{p.score:.1f}",
            f"@{p.author_username}",
            format_count(p.likes),
            snippet,
        )
    console.print(table)

    indices = None
    if blocking:
        raw = typer.prompt(
            f"Pick numbers (comma-separated), empty = top {cfg.curation.top_n}",
            default="",
        )
        indices = parse_indices(raw)

    picks = select_picks(scored, top_n=cfg.curation.top_n, indices=indices)
    md_path = run_dir / "candidates.md"
    md_path.write_text(
        render_candidates_md(scored, date=run_dir.name, kept_ids={p.id for p in picks}),
        encoding="utf-8",
    )
    write_picks(
        dest,
        picks,
        meta={
            "date": run_dir.name,
            "auto": not blocking,
            "scored": len(scored),
            "top_n": cfg.curation.top_n,
        },
    )
    write_json(run_dir / "scored.json", {"items": [p.model_dump() for p in scored]})
    if picks:
        ledger.mark_picks((p.id for p in picks), extra={"date": run_dir.name})
        ledger.save()

    typer.secho(
        f"curate: {len(picks)} pick(s) → {dest}  (review {md_path})",
        fg=typer.colors.GREEN,
    )
