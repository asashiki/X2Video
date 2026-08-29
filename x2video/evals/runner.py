"""Run deterministic smoke evaluation and write JSON, Markdown, and HTML reports."""

from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from uuid import uuid4

from x2video.application import ApplicationService
from x2video.domain.models import EvalCase, EvalResult
from x2video.tools.content import _probe_media_checks


def _load_cases() -> list[EvalCase]:
    path = Path(__file__).with_name("cases.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase(run_id="eval_suite", **item) for item in payload]


def _baseline_capabilities() -> dict[str, bool]:
    return {case.expected["capability"]: False for case in _load_cases()} | {
        "no_media_handling": True,
        "publish_kit": True,
    }


def _v02_capabilities() -> tuple[dict[str, bool], dict[str, object]]:
    with tempfile.TemporaryDirectory(prefix="x2video-eval-") as directory:
        service = ApplicationService(work_dir=directory)
        created = service.create_run(query="今日 AI 圈三件事", autonomy="auto")
        run_id = created["run"]["run_id"]
        service.execute_sync(run_id)
        snapshot = service.get_run(run_id) or {}
        decisions = snapshot.get("decisions", [])
        selected = [item for item in decisions if item.get("selected")]
        evidence = {item["candidate_id"]: item for item in snapshot.get("evidence", [])}
        script = snapshot.get("documents", {}).get("script.final.json", {})
        segments = script.get("segments", [])
        review = snapshot.get("documents", {}).get("script.review.json", {})
        before = snapshot.get("documents", {}).get("publish_kit/qc.before.json", {})
        after = snapshot.get("documents", {}).get("publish_kit/qc.after.json", {})
        video_path = Path(directory) / "agent_runs" / run_id / "publish_kit" / "video.mp4"
        event_text = json.dumps(snapshot.get("events", []), ensure_ascii=False).lower()
        defect_checks = _quality_defect_smoke(Path(directory))
        context_fixture = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "evals" / "context_candidates.json"
        context_created = service.create_run(query="Thread、Quote 与 Meme 上下文", autonomy="auto")
        context_run_id = context_created["run"]["run_id"]
        asyncio.run(
            service.runtime.run(
                context_run_id,
                payload={"fixture_path": str(context_fixture)},
            )
        )
        context_snapshot = service.get_run(context_run_id) or {}
        context_evidence = context_snapshot.get("evidence", [])
        context_types = {
            source.get("source_type")
            for pack in context_evidence
            for source in pack.get("sources", [])
        }
        context_curation = context_snapshot.get("documents", {}).get("curation.json", {})
        capabilities = {
            "evidence_coverage": bool(selected) and all(item["candidate_id"] in evidence for item in selected),
            "claim_grounding": bool(segments) and all(item.get("evidence_ids") for item in segments),
            "injection_detection": any(
                any(str(flag).startswith("prompt_injection") for flag in item.get("risk_flags", []))
                for item in evidence.values()
            ),
            "injection_rejection": all(not item.get("selected") for item in decisions if "prompt_injection" in item.get("risk_flags", [])),
            "deduplication": all(not item.get("selected") for item in decisions if item.get("candidate_id") == "demo-005"),
            "portfolio_selection": len(selected) == 3,
            "thread_context": "x_thread" in context_types,
            "quote_context": "x_quote" in context_types,
            "meme_risk": any(
                "meme_or_satire" in pack.get("risk_flags", []) for pack in context_evidence
            ),
            "no_media_handling": any(item.get("candidate_id") == "demo-003" for item in selected),
            "multilingual_grounding": any(
                "multilingual" in str(item).lower() or "多语言" in str(item) for item in segments
            ),
            "high_risk_block": all(not item.get("selected") for item in decisions if item.get("risk_flags")),
            "candidate_shortage": bool(context_curation.get("candidate_shortage")),
            "bounded_retry": all(int(task.get("max_attempts", 0)) <= 2 for task in snapshot.get("tasks", [])),
            "safe_area_repair": bool(before.get("issues")) and bool(after.get("ok")),
            "black_frame_detection": defect_checks["black_frame_detection"],
            "silence_detection": defect_checks["silence_detection"],
            "loudness_detection": defect_checks["loudness_detection"],
            "budget_guard": bool(snapshot.get("goal", {}).get("budget")),
            "idempotency": all(task.get("status") in {"succeeded", "skipped"} for task in snapshot.get("tasks", [])),
            "replay": service.runtime.replay(run_id).get("event_count", 0) > 0,
            "trace_redaction": not any(token in event_text for token in ("bearer ", "api_key", "cookie=")),
            "grounded_script": bool(segments),
            "segment_patch": len(review.get("diffs", [])) == 1,
            "bounded_repairs": int(review.get("rounds", 99)) <= 2 and len(after.get("actions", [])) <= 2,
            "segment_lock": bool(segments) and all("locked" in item for item in segments),
            "confidence_visibility": bool(evidence) and all("overall_confidence" in item for item in evidence.values()),
            "decision_rationale": bool(decisions) and all(item.get("decision_summary") for item in decisions),
            "human_gates": any(task.get("human_gate") for task in snapshot.get("plan", {}).get("tasks", [])),
            "publish_kit": video_path.exists() and video_path.stat().st_size > 10_000 and bool(after),
        }
        proof = {
            "run_id": run_id,
            "event_count": len(snapshot.get("events", [])),
            "selected_count": len(selected),
            "video_bytes": video_path.stat().st_size if video_path.exists() else 0,
            "context_run_id": context_run_id,
        }
        return capabilities, proof


def _quality_defect_smoke(root: Path) -> dict[str, bool]:
    black = root / "eval-black-silent.mp4"
    loud = root / "eval-loud.mp4"
    commands = [
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=black:s=160x240:d=0.8",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "0.8",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(black),
        ],
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=blue:s=160x240:d=0.8",
            "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=0.8",
            "-t", "0.8", "-c:v", "libx264", "-c:a", "aac", "-shortest", str(loud),
        ],
    ]
    for command in commands:
        subprocess.run(command, check=True, capture_output=True)
    black_checks = _probe_media_checks(black)
    loud_checks = _probe_media_checks(loud)
    return {
        "black_frame_detection": bool(black_checks["black_segments"]),
        "silence_detection": bool(black_checks["silence_segments"]),
        "loudness_detection": bool(
            loud_checks["mean_volume_db"] is not None and loud_checks["mean_volume_db"] > -30
        ),
    }


def run_evaluation(*, profile: str = "v0.2", output_dir: str | Path = "evals/reports") -> dict[str, object]:
    if profile not in {"baseline", "v0.2"}:
        raise ValueError("profile must be baseline or v0.2")
    cases = _load_cases()
    if profile == "baseline":
        capabilities, proof = _baseline_capabilities(), {"source": "v0.1 frozen capability baseline"}
    else:
        capabilities, proof = _v02_capabilities()
    run_id = f"eval_{profile.replace('.', '')}_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}_{uuid4().hex[:6]}"
    results = []
    for case in cases:
        capability = str(case.expected["capability"])
        passed = bool(capabilities.get(capability, False))
        results.append(
            EvalResult(
                run_id=run_id,
                case_id=case.case_id,
                passed=passed,
                metrics={"deterministic": float(passed), "semantic": 1.0 if passed else 0.0},
                issues=[] if passed else [f"Capability not yet demonstrated: {capability}"],
                baseline_id="v0.1" if profile == "baseline" else None,
            ).model_dump(mode="json")
        )
    passed_count = sum(item["passed"] for item in results)
    report: dict[str, object] = {
        "schema_version": "1.0",
        "report_id": run_id,
        "profile": profile,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_size": len(cases),
        "summary": {
            "passed": passed_count,
            "failed": len(cases) - passed_count,
            "pass_rate": passed_count / len(cases),
        },
        "proof": proof,
        "results": results,
    }
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{run_id}.json"
    markdown_path = output / f"{run_id}.md"
    html_path = output / f"{run_id}.html"
    report["paths"] = {
        "json": str(json_path),
        "markdown": str(markdown_path),
        "html": str(html_path),
    }
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = _markdown(report, cases)
    markdown_path.write_text(markdown, encoding="utf-8")
    html_path.write_text(_html(report, markdown), encoding="utf-8")
    return report


def compare_reports(baseline_id: str, new_id: str, *, reports_dir: str | Path = "evals/reports") -> dict[str, object]:
    root = Path(reports_dir)
    baseline = json.loads((root / f"{baseline_id}.json").read_text(encoding="utf-8"))
    current = json.loads((root / f"{new_id}.json").read_text(encoding="utf-8"))
    comparison_id = f"compare_{baseline_id}_to_{new_id}"
    delta = current["summary"]["pass_rate"] - baseline["summary"]["pass_rate"]
    result = {
        "schema_version": "1.0",
        "comparison_id": comparison_id,
        "baseline_id": baseline_id,
        "new_id": new_id,
        "baseline_pass_rate": baseline["summary"]["pass_rate"],
        "new_pass_rate": current["summary"]["pass_rate"],
        "pass_rate_delta": delta,
    }
    json_path = root / f"{comparison_id}.json"
    markdown_path = root / f"{comparison_id}.md"
    result["markdown_path"] = str(markdown_path)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        "# Eval comparison\n\n"
        f"- Baseline: `{baseline_id}` — {result['baseline_pass_rate']:.1%}\n"
        f"- New: `{new_id}` — {result['new_pass_rate']:.1%}\n"
        f"- Delta: **{delta:+.1%}**\n",
        encoding="utf-8",
    )
    return result


def _markdown(report: dict[str, object], cases: list[EvalCase]) -> str:
    summary = report["summary"]
    results = report["results"]
    case_map = {case.case_id: case for case in cases}
    rows = ["# X2Video evaluation", "", f"- Report: `{report['report_id']}`", f"- Profile: `{report['profile']}`", f"- Pass rate: **{summary['pass_rate']:.1%}** ({summary['passed']}/{report['dataset_size']})", "", "| Case | Category | Result |", "|---|---|---|"]
    for item in results:
        case = case_map[item["case_id"]]
        rows.append(f"| {case.name} | {case.category} | {'PASS' if item['passed'] else 'GAP'} |")
    return "\n".join(rows) + "\n"


def _html(report: dict[str, object], markdown: str) -> str:
    return (
        "<!doctype html><meta charset='utf-8'><title>X2Video Eval</title>"
        "<style>body{max-width:980px;margin:40px auto;background:#0a0d12;color:#edf1f7;"
        "font:15px system-ui;white-space:pre-wrap}code{color:#f1ae52}</style>"
        f"<body><pre>{escape(markdown)}</pre></body>"
    )
