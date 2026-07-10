"""Generate Chinese narration script."""

from pathlib import Path

import typer

app = typer.Typer(help="Generate Chinese narration script")


@app.callback(invoke_without_command=True)
def script(
    ctx: typer.Context,
    picks: Path = typer.Option(
        Path("work/picks.json"),
        "--input",
        "-i",
        help="Path to picks JSON from curate",
    ),
    output: Path = typer.Option(
        Path("work/script.md"),
        "--output",
        "-o",
        help="Output path for the narration script",
    ),
) -> None:
    """Generate a Chinese narration script for the digest (N-segment, N=1 for
    single tweet)."""
    typer.echo(f"script: stub — input={picks}, output={output}")
