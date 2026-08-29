"""Execute the full pipeline end-to-end."""

from __future__ import annotations

import typer

from x2video.cli.common import die
from x2video.pipeline.orchestrate import STAGES, run_pipeline

app = typer.Typer(help="Execute the full pipeline end-to-end")


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    date: str | None = typer.Option(None, "--date", help="Run date YYYY-MM-DD (default: today)"),
    auto: bool = typer.Option(
        False,
        "--auto",
        help="Skip Gate 1 prompt and take top N picks",
    ),
    from_stage: str = typer.Option(
        "fetch",
        "--from-stage",
        help="Resume from this stage (fetch|curate|card|script|render)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Redo stages even if their outputs already exist",
    ),
    skip_hard_filter: bool = typer.Option(False, "--skip-hard-filter"),
    skip_ledger: bool = typer.Option(False, "--skip-ledger"),
    autonomy: str | None = typer.Option(
        None,
        "--autonomy",
        help="Compatibility autonomy: supervised, assisted, or auto",
    ),
) -> None:
    """Run the full pipeline: fetch → curate → card → script → render.

    Existing artifacts in work/YYYY-MM-DD/ are reused unless --force is set.
    """
    cfg = ctx.obj
    if from_stage not in STAGES:
        die(f"Unknown stage '{from_stage}'. Use: {', '.join(STAGES)}")

    if autonomy not in {None, "supervised", "assisted", "auto"}:
        die("--autonomy must be supervised, assisted, or auto")
    use_auto = auto or autonomy == "auto" or (not cfg.curation.blocking_mode)
    if not use_auto:
        typer.echo(
            "Gate 1 is blocking. Re-run with --auto, or set [curation].blocking_mode = false."
        )
        typer.echo("Running fetch first, then dropping to `x2video curate` for the prompt.")

    def on_stage(stage: str, status: str) -> None:
        typer.echo(f"run: {stage} {status}")

    try:
        result = run_pipeline(
            cfg,
            date=date,
            auto=use_auto,
            from_stage=from_stage,
            force=force,
            skip_hard_filter=skip_hard_filter,
            skip_ledger=skip_ledger,
            on_stage=on_stage,
        )
    except Exception as exc:
        die(f"run failed: {exc}")

    render = result["stages"].get("render") or {}
    kit = render.get("kit_dir") if isinstance(render, dict) else None
    typer.secho(
        f"run: done  work={result['run_dir']}" + (f"  kit={kit}" if kit else ""),
        fg=typer.colors.GREEN,
    )
