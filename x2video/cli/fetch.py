"""Fetch candidates from the configured data source."""

from __future__ import annotations

from pathlib import Path

import typer

from x2video.auth.oauth import GrokLoginRequiredError
from x2video.cli.common import die
from x2video.pipeline.fetch import run_fetch

app = typer.Typer(help="Fetch candidates from X and apply hard filters")


@app.callback(invoke_without_command=True)
def fetch(
    ctx: typer.Context,
    keywords: list[str] = typer.Option(
        None, "--keyword", "-k", help="Domain keywords to search (overrides config)"
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path (default: work/YYYY-MM-DD/candidates.json)",
    ),
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help='Override source provider for this run ("grok" or "x_mcp")',
    ),
    max_results: int | None = typer.Option(
        None,
        "--max",
        help="Max candidates to keep (default: curation.max_candidates)",
    ),
    skip_hard_filter: bool = typer.Option(
        False,
        "--skip-hard-filter",
        help="Keep all source results without engagement thresholds",
    ),
    skip_ledger: bool = typer.Option(
        False,
        "--skip-ledger",
        help="Do not drop IDs already recorded in the ledger",
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

    typer.echo(
        f"fetch: provider={cfg.source.provider} "
        f"keywords={keywords or cfg.domain_keywords} "
        f"window={cfg.hard_filter.time_window_hours}h"
    )
    try:
        result = run_fetch(
            cfg,
            keywords=keywords,
            max_results=max_results,
            skip_hard_filter=skip_hard_filter,
            skip_ledger=skip_ledger,
            date=date,
            output=output,
        )
    except GrokLoginRequiredError as exc:
        die(str(exc))
    except NotImplementedError as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(code=2) from exc
    except Exception as exc:
        die(f"fetch failed: {exc}")

    typer.secho(
        f"fetch: wrote {result['kept']}/{result['fetched']} candidates → {result['output']}",
        fg=typer.colors.GREEN,
    )
