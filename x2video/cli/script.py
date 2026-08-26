"""Generate Chinese narration script."""

from pathlib import Path

import typer

from x2video.cli.common import die, run_async
from x2video.pipeline.script import run_script

app = typer.Typer(help="Generate Chinese narration script")


@app.callback(invoke_without_command=True)
def script(
    ctx: typer.Context,
    picks: Path | None = typer.Option(
        None,
        "--input",
        "-i",
        help="Path to picks JSON from curate",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for the narration script JSON",
    ),
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
) -> None:
    """Generate a Chinese narration script for the digest (N-segment, N=1 for
    single tweet)."""
    cfg = ctx.obj
    try:
        result = run_async(run_script(cfg, date=date, input_path=picks, output_path=output))
    except Exception as exc:
        die(f"script failed: {exc}")
    typer.secho(
        f"script: N={result['n']} → {result['output']}  ({result['markdown']})",
        fg=typer.colors.GREEN,
    )
