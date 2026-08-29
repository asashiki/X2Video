"""Run Demo Mode repeatedly and record real state, media, QC, and timing proof."""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path

from x2video.application import ApplicationService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--work-dir", default="work/demo-stability")
    parser.add_argument("--report", default="artifacts/demo-stability.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    service = ApplicationService(work_dir=str(root / args.work_dir))
    results = []
    for index in range(args.runs):
        started = time.monotonic()
        created = service.create_run(
            query="做一条 60 秒以内的今日 AI 新闻，三条以内，避免重复，优先可信信息。",
            autonomy="auto",
        )
        run_id = created["run"]["run_id"]
        snapshot = service.execute_sync(run_id)
        publish = root / args.work_dir / "agent_runs" / run_id / "publish_kit"
        qc = json.loads((publish / "qc.after.json").read_text(encoding="utf-8"))
        results.append(
            {
                "iteration": index + 1,
                "run_id": run_id,
                "state": snapshot["run"]["state"],
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "event_count": len(snapshot["events"]),
                "video_bytes": (publish / "video.mp4").stat().st_size,
                "qc_ok": qc["ok"],
                "repair_count": len(qc["actions"]),
            }
        )
    report = {
        "schema_version": "1.0",
        "created_at": datetime.now(UTC).isoformat(),
        "requested_runs": args.runs,
        "successful_runs": sum(item["state"] == "COMPLETE" and item["qc_ok"] for item in results),
        "total_seconds": round(sum(item["elapsed_seconds"] for item in results), 3),
        "results": results,
    }
    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"successful={report['successful_runs']}/{args.runs} report={report_path}")
    if report["successful_runs"] != args.runs:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
