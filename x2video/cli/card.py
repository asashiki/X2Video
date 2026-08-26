"""Render bilingual tweet cards."""

from pathlib import Path

import typer

from x2video.cli.common import die
from x2video.pipeline.card import run_card

app = typer.Typer(help="Render bilingual tweet cards")


@app.callback(invoke_without_command=True)
def card(
    ctx: typer.Context,
    picks: Path | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to picks JSON from curate",
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory for rendered card images",
    ),
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
) -> None:
    """Render bilingual tweet cards (original + Chinese translation overlay)."""
    cfg = ctx.obj
    try:
        result = run_card(cfg, date=date, input_path=picks, output_dir=output_dir)
    except Exception as exc:
        die(f"card failed: {exc}")
    typer.secho(
        f"card: wrote {result['count']} PNG(s) → {result['output_dir']}",
        fg=typer.colors.GREEN,
    )
