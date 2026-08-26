"""X2Video CLI entry point.

Mounts pipeline subcommands under a single Typer app.
"""

from __future__ import annotations

import typer
from rich.console import Console

from x2video.cli import auth, card, curate, doctor, fetch, render, run, script
from x2video.config.loader import load_config

console = Console(stderr=True)

app = typer.Typer(
    name="x2video",
    help="Fetch X/Twitter hot posts and synthesize vertical short videos.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

_NO_CONFIG = {"auth", "doctor"}


@app.callback()
def main(
    ctx: typer.Context,
    config: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file [default: auto-detect from ./x2video.toml etc.]",
    ),
) -> None:
    """X2Video — automated pipeline from tweets to publish kit."""
    if ctx.invoked_subcommand in _NO_CONFIG:
        ctx.obj = None
        return
    try:
        ctx.obj = load_config(config)
    except FileNotFoundError:
        console.print("[red]Config file not found.[/red]")
        raise typer.Exit(code=1)
    except ValueError as exc:
        console.print(f"[red]Config validation failed:[/red] {exc}")
        raise typer.Exit(code=1)


app.add_typer(
    auth.app,
    name="auth",
    help="Login / logout SuperGrok subscription (browser OAuth)",
)
app.add_typer(doctor.app, name="doctor", help="Check ffmpeg, Playwright, auth, and config")
app.add_typer(fetch.app, name="fetch", help="Fetch candidates from X and apply hard filters")
app.add_typer(curate.app, name="curate", help="Score candidates via LLM curation and select picks")
app.add_typer(card.app, name="card", help="Render bilingual tweet cards")
app.add_typer(script.app, name="script", help="Generate Chinese narration script")
app.add_typer(render.app, name="render", help="Synthesize TTS audio and compose final MP4")
app.add_typer(run.app, name="run", help="Execute the full pipeline end-to-end")
