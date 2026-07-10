"""Render bilingual tweet cards."""

from pathlib import Path

import typer

app = typer.Typer(help="Render bilingual tweet cards")


@app.callback(invoke_without_command=True)
def card(
    ctx: typer.Context,
    picks: Path = typer.Option(
        Path("work/picks.json"),
        "--input",
        "-i",
        help="Path to picks JSON from curate",
    ),
    output_dir: Path = typer.Option(
        Path("work/cards"),
        "--output-dir",
        "-o",
        help="Directory for rendered card images",
    ),
) -> None:
    """Render bilingual tweet cards (original + Chinese translation overlay)."""
    typer.echo(f"card: stub — input={picks}, output_dir={output_dir}")
