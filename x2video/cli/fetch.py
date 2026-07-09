"""Fetch candidates from X (Twitter)."""

from pathlib import Path

import typer

app = typer.Typer(help="Fetch candidates from X and apply hard filters")


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
) -> None:
    """Fetch recent tweets matching domain keywords, apply hard filters,
    and deduplicate via ledger."""
    cfg = ctx.obj
    kw = keywords or cfg.domain_keywords
    typer.echo(f"fetch: stub — keywords={kw}, output={output}")
