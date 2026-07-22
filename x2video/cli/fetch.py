"""Fetch candidates from the configured data source."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from x2video.auth.oauth import GrokLoginRequiredError
from x2video.source.factory import create_source

app = typer.Typer(help="Fetch candidates from X and apply hard filters")


def _passes_hard_filter(
    likes: int,
    retweets: int,
    replies: int,
    views: int,
    *,
    min_likes: int,
    min_retweets: int,
    min_replies: int,
    views_threshold: int,
) -> bool:
    if likes < min_likes:
        return False
    if retweets < min_retweets:
        return False
    if replies < min_replies:
        return False
    if views_threshold > 0 and views < views_threshold:
        return False
    return True


@app.callback(invoke_without_command=True)
def fetch(
    ctx: typer.Context,
    keywords: list[str] = typer.Option(
        None, "--keyword", "-k", help="Domain keywords to search (overrides config)"
    ),
    output: Path = typer.Option(
        Path("work/candidates.json"),
        "--output",
        "-o",
        help="Output path for fetched candidates",
    ),
    provider: str = typer.Option(
        None,
        "--provider",
        "-p",
        help='Override source provider for this run ("grok" or "x_mcp")',
    ),
    max_results: int = typer.Option(
        None,
        "--max",
        help="Max candidates to keep (default: curation.max_candidates)",
    ),
    skip_hard_filter: bool = typer.Option(
        False,
        "--skip-hard-filter",
        help="Keep all source results without engagement thresholds",
    ),
) -> None:
    """Fetch recent tweets matching domain keywords, apply hard filters,
    and write candidates JSON.

    Data source is selected by ``[source].provider``:

    * ``x_mcp`` — X official MCP (Bearer token; issue #1)
    * ``grok``  — SuperGrok OAuth + X Search (run ``x2video auth login`` first)
    """
    cfg = ctx.obj
    if provider:
        cfg.source.provider = provider

    kw = list(keywords) if keywords else list(cfg.domain_keywords)
    if not kw:
        typer.secho("No domain keywords configured.", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

    limit = max_results if max_results is not None else cfg.curation.max_candidates
    hf = cfg.hard_filter

    try:
        source = create_source(cfg)
    except ValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(
        f"fetch: provider={source.name} keywords={kw} "
        f"window={hf.time_window_hours}h max={limit}"
    )

    try:
        raw = source.fetch(
            kw,
            time_window_hours=hf.time_window_hours,
            max_results=max(limit * 2, limit),  # oversample before hard filter
        )
    except GrokLoginRequiredError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    except NotImplementedError as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        typer.secho(f"fetch failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if skip_hard_filter:
        filtered = raw
    else:
        filtered = [
            c
            for c in raw
            if _passes_hard_filter(
                c.likes,
                c.retweets,
                c.replies,
                c.views,
                min_likes=hf.min_likes,
                min_retweets=hf.min_retweets,
                min_replies=hf.min_replies,
                views_threshold=hf.views_threshold,
            )
        ]

    # Rank by engagement, keep top limit
    filtered.sort(key=lambda c: c.engagement_score(), reverse=True)
    filtered = filtered[:limit]

    payload = {
        "provider": source.name,
        "keywords": kw,
        "time_window_hours": hf.time_window_hours,
        "fetched": len(raw),
        "kept": len(filtered),
        "candidates": [c.model_dump() for c in filtered],
    }

    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    typer.secho(
        f"fetch: wrote {len(filtered)}/{len(raw)} candidates → {output}",
        fg=typer.colors.GREEN,
    )
