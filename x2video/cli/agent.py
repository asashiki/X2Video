"""Commands for the bounded Content Director runtime."""

from __future__ import annotations

import json
import os

import typer

from x2video.application import ApplicationService

app = typer.Typer(help="Create and execute bounded Agent Studio runs")


@app.command("run")
def run_agent(
    goal: str = typer.Option(..., "--goal", help="Natural-language content goal"),
    autonomy: str = typer.Option("assisted", help="supervised, assisted, or auto"),
    duration: int = typer.Option(60, min=15, max=600, help="Target duration in seconds"),
    wait: bool = typer.Option(True, "--wait/--background", help="Wait for the current run state"),
    work_dir: str = typer.Option(None, help="Agent control-plane directory"),
) -> None:
    """Create a versioned Goal and execute its bounded plan using Demo fixtures."""
    if autonomy not in {"supervised", "assisted", "auto"}:
        raise typer.BadParameter("must be supervised, assisted, or auto", param_hint="autonomy")
    service = ApplicationService(work_dir=work_dir or os.environ.get("X2VIDEO_WORK_DIR", "work"))
    snapshot = service.create_run(
        query=goal,
        autonomy=autonomy,
        target_duration_seconds=duration,
    )
    run_id = snapshot["run"]["run_id"]
    if wait:
        snapshot = service.execute_sync(run_id)
        typer.echo(json.dumps({"run_id": run_id, "state": snapshot["run"]["state"]}, ensure_ascii=False))
    else:
        pid = service.start_worker(run_id)
        typer.echo(json.dumps({"run_id": run_id, "worker_pid": pid}, ensure_ascii=False))
