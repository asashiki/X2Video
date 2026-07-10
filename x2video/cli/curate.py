"""Score and select picks via LLM curation."""

from pathlib import Path

import typer

app = typer.Typer(help="Score candidates via LLM curation and select picks")


@app.callback(invoke_without_command=True)
def curate(
    ctx: typer.Context,
    candidates: Path = typer.Option(
        Path("work/candidates.json"),
        "--input",
        "-i",
        help="Path to candidates JSON from fetch",
    ),
    output: Path = typer.Option(
        Path("work/picks.json"), "--output", "-o", help="Output path for selected picks"
    ),
    auto: bool | None = typer.Option(
        None, "--auto/--no-auto", help="Override blocking mode from config"
    ),
) -> None:
    """Score candidates via LLM curation and produce a ranked pick list."""
    cfg = ctx.obj
    blocking = auto if auto is not None else cfg.curation.blocking_mode
    typer.echo(f"curate: stub — input={candidates}, output={output}, blocking={blocking}")
