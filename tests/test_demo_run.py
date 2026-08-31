from pathlib import Path

import pytest

from x2video.agent.planner import build_plan
from x2video.agent.runtime import AgentRuntime
from x2video.domain.models import ContentGoal
from x2video.storage.run_store import RunStore
from x2video.tools.content import register_content_tools
from x2video.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_demo_run_proves_evidence_patch_and_repair(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "agent.db")
    registry = ToolRegistry()
    register_content_tools(registry, store)
    runtime = AgentRuntime(store, registry, work_dir=str(tmp_path))
    goal = ContentGoal(run_id="run_demo", query="今日 AI 圈三件事", autonomy="auto")
    runtime.create(goal, build_plan(goal))

    snapshot = await runtime.run("run_demo")

    assert snapshot["run"]["state"] == "COMPLETE"
    assert len(snapshot["evidence"]) == 5
    assert sum(item["selected"] for item in snapshot["decisions"]) == 3
    assert snapshot["script_issues"][0]["resolved"] is True
    assert snapshot["quality_issues"][0]["resolved"] is True

    run_dir = tmp_path / "agent_runs" / "run_demo"
    script = (run_dir / "script.final.json").read_text(encoding="utf-8")
    assert "全面开放" not in script
    assert "向部分账号向部分账号" not in script
    assert "向部分账号逐步开放" in script
    manifest = (run_dir / "publish_kit" / "render_manifest.json").read_text(encoding="utf-8")
    assert '"subtitle_bottom": 1620' in manifest
    assert (run_dir / "publish_kit" / "video.mp4").stat().st_size > 10_000
