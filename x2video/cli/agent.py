"""Commands for the bounded Content Director runtime."""

from __future__ import annotations

import json
import os

import typer

from x2video.application import ApplicationService
from x2video.config.loader import load_config

app = typer.Typer(help="Create and execute bounded Agent Studio runs")


@app.command("run")
def run_agent(
    goal: str = typer.Option(..., "--goal", help="Natural-language content goal"),
    autonomy: str = typer.Option("assisted", help="supervised, assisted, or auto"),
    duration: int = typer.Option(60, min=15, max=600, help="Target duration in seconds"),
    wait: bool = typer.Option(True, "--wait/--background", help="Wait for the current run state"),
    work_dir: str = typer.Option(None, help="Agent control-plane directory"),
    demo: bool = typer.Option(False, "--demo", help="Force offline Demo fixtures"),
    live: bool = typer.Option(False, "--live", help="Force the configured X source + original pipeline"),
) -> None:
    """Create a Goal and run it. Uses the original X pipeline when SuperGrok is logged in."""
    if autonomy not in {"supervised", "assisted", "auto"}:
        raise typer.BadParameter("must be supervised, assisted, or auto", param_hint="autonomy")
    if demo and live:
        raise typer.BadParameter("use either --demo or --live", param_hint="live")
    try:
        config = load_config()
    except Exception:
        config = None
    service = ApplicationService(
        work_dir=work_dir or os.environ.get("X2VIDEO_WORK_DIR", "work"),
        config=config,
    )
    mode = "demo" if demo else "live" if live else None
    snapshot = service.create_run(
        query=goal,
        autonomy=autonomy,
        target_duration_seconds=duration,
        mode=mode,
    )
    run_id = snapshot["run"]["run_id"]
    if wait:
        snapshot = service.execute_sync(run_id)
        typer.echo(json.dumps({"run_id": run_id, "state": snapshot["run"]["state"]}, ensure_ascii=False))
    else:
        pid = service.start_worker(run_id)
        typer.echo(json.dumps({"run_id": run_id, "worker_pid": pid}, ensure_ascii=False))
