"""Synthesize TTS audio and compose the final vertical MP4."""

from pathlib import Path

import typer

app = typer.Typer(help="Synthesize TTS audio and compose final MP4")


@app.callback(invoke_without_command=True)
def render(
    ctx: typer.Context,
    script_file: Path = typer.Option(
        Path("work/script.md"), "--script", "-s", help="Path to narration script"
    ),
    cards_dir: Path = typer.Option(
        Path("work/cards"), "--cards", help="Directory containing rendered card images"
    ),
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Publish kit output directory (default: final/<timestamp>)",
    ),
) -> None:
    """Synthesize TTS audio from script, then compose cards + audio + subtitles
    into a 1080x1920 MP4 publish kit."""
    cfg = ctx.obj
    od = output_dir or Path(cfg.final_dir) / "<timestamp>"
    typer.echo(f"render: stub — script={script_file}, cards={cards_dir}, output={od}")
