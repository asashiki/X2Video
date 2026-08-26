"""Synthesize TTS audio and compose the final vertical MP4."""

from pathlib import Path

import typer

from x2video.cli.common import die, run_async
from x2video.pipeline.render import run_render

app = typer.Typer(help="Synthesize TTS audio and compose final MP4")


@app.callback(invoke_without_command=True)
def render(
    ctx: typer.Context,
    script_file: Path | None = typer.Option(
        None, "--script", "-s", help="Path to narration script JSON"
    ),
    cards_dir: Path | None = typer.Option(
        None, "--cards", help="Directory containing rendered card images"
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Publish kit output directory (default: final/<timestamp>)",
    ),
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
) -> None:
    """Synthesize TTS audio from script, then compose cards + audio + subtitles
    into a 1080x1920 MP4 publish kit."""
    cfg = ctx.obj
    try:
        result = run_async(
            run_render(
                cfg,
                date=date,
                script_path=script_file,
                cards_dir=cards_dir,
                output_dir=output_dir,
            )
        )
    except Exception as exc:
        die(f"render failed: {exc}")
    typer.secho(
        f"render: Publish Kit → {result['kit_dir']}",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"  video: {result['video']}")
    typer.echo(f"  cover: {result['cover']}")
    typer.echo(f"  copy:  {result['publish_md']}")
