"""Fixed-dataset evaluation and report comparison commands."""

from __future__ import annotations

from pathlib import Path

import typer

from x2video.evals.runner import compare_reports, run_evaluation

app = typer.Typer(help="Run and compare the fixed Agent Studio evaluation suite")


@app.command("run")
def run_eval(
    profile: str = typer.Option("v0.2", help="Evaluation profile: baseline or v0.2"),
    output_dir: Path = typer.Option(Path("evals/reports"), help="Report output directory"),
) -> None:
    report = run_evaluation(profile=profile, output_dir=output_dir)
    typer.echo(f"{report['report_id']} {report['summary']['pass_rate']:.1%} {report['paths']['markdown']}")


@app.command("compare")
def compare_eval(
    baseline_id: str,
    new_id: str,
    reports_dir: Path = typer.Option(Path("evals/reports"), help="Report directory"),
) -> None:
    result = compare_reports(baseline_id, new_id, reports_dir=reports_dir)
    typer.echo(f"{result['comparison_id']} delta={result['pass_rate_delta']:+.1%} {result['markdown_path']}")
