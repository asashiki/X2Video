"""X2Video CLI entry point.

Mounts the six pipeline subcommands under a single Typer app.

Error handling convention (to be implemented as pipeline stages go live):
    try:
        cfg = load_config(config)
    except FileNotFoundError:
        rich.print("[red]Config file not found.[/red]")
        raise typer.Exit(code=1)
    except ValueError as e:
        rich.print(f"[red]Config validation failed:[/red] {e}")
        raise typer.Exit(code=1)

Subcommand-level errors (API failures, missing keys) are handled
inside each subcommand, not here.
"""

import typer

from x2video.cli import auth, fetch, curate, card, script, render, run
from x2video.config.loader import load_config

app = typer.Typer(
    name="x2video",
    help="Fetch X/Twitter hot posts and synthesize vertical short videos.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback()
def main(
    ctx: typer.Context,
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file [default: auto-detect from ./x2video.toml etc.]",
    ),
) -> None:
    """X2Video — automated pipeline from tweets to publish kit."""
    # Auth subcommands do not need a full config (and should work pre-setup).
    if ctx.invoked_subcommand == "auth":
        ctx.obj = None
        return
    ctx.obj = load_config(config)


app.add_typer(
    auth.app,
    name="auth",
    help="Login / logout SuperGrok subscription (browser OAuth)",
)
app.add_typer(fetch.app, name="fetch", help="Fetch candidates from X and apply hard filters")
app.add_typer(curate.app, name="curate", help="Score candidates via LLM curation and select picks")
app.add_typer(card.app, name="card", help="Render bilingual tweet cards")
app.add_typer(script.app, name="script", help="Generate Chinese narration script")
app.add_typer(render.app, name="render", help="Synthesize TTS audio and compose final MP4")
app.add_typer(run.app, name="run", help="Execute the full pipeline end-to-end")
