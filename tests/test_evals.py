from pathlib import Path

from x2video.evals.runner import compare_reports, run_evaluation


def test_eval_writes_three_formats_and_compares(tmp_path: Path) -> None:
    baseline = run_evaluation(profile="baseline", output_dir=tmp_path)
    current = run_evaluation(profile="v0.2", output_dir=tmp_path)

    assert baseline["dataset_size"] == 30
    assert current["summary"]["pass_rate"] > baseline["summary"]["pass_rate"]
    for path in current["paths"].values():
        assert Path(path).exists()

    comparison = compare_reports(
        baseline["report_id"],
        current["report_id"],
        reports_dir=tmp_path,
    )
    assert comparison["pass_rate_delta"] > 0
    assert Path(comparison["markdown_path"]).exists()
