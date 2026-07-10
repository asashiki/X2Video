"""Execute the full pipeline end-to-end."""

import typer

app = typer.Typer(help="Execute the full pipeline end-to-end")


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
) -> None:
    """Run the full pipeline: fetch → curate → card → script → render.

    Each stage reads outputs from the previous stage. Configuration
    (including blocking mode for Gate 1) is driven by the config file.
    """
    cfg = ctx.obj
    typer.echo(f"run: stub — pipeline from {cfg.work_dir}/ to {cfg.final_dir}/")
