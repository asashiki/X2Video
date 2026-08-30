from __future__ import annotations

from pathlib import Path

import pytest

from x2video.agent.runtime import AgentRuntime
from x2video.domain.models import ContentGoal, PlanTask, RunPlan, RunState
from x2video.storage.run_store import RunStore
from x2video.tools.base import AgentTool, ToolContext, ToolResult
from x2video.tools.registry import ToolRegistry


class CountingTool(AgentTool):
    name = "test.count"

    def __init__(self, *, fail_once: bool = False) -> None:
        self.calls = 0
        self.fail_once = fail_once

    async def execute(self, context: ToolContext) -> ToolResult:
        self.calls += 1
        if self.fail_once and self.calls == 1:
            raise RuntimeError("transient")
        return ToolResult(summary="counted", payload={"calls": self.calls})


def _runtime(tmp_path: Path, *, autonomy: str = "supervised", fail_once: bool = False):
    store = RunStore(tmp_path / "agent.db")
    registry = ToolRegistry()
    tool = CountingTool(fail_once=fail_once)
    registry.register(tool)
    goal = ContentGoal(run_id="run_test", query="AI", autonomy=autonomy)
    first = PlanTask(
        task_type="count",
        target_state=RunState.DISCOVER,
        tool_name=tool.name,
        max_attempts=2,
    )
    gate = PlanTask(
        task_type="gate_2",
        target_state=RunState.WAIT_GATE_2,
        depends_on=[first.task_id],
        human_gate=True,
    )
    plan = RunPlan(
        run_id=goal.run_id,
        format="news_recap",
        tasks=[first, gate],
        decision_summary="test plan",
    )
    runtime = AgentRuntime(store, registry, work_dir=str(tmp_path))
    runtime.create(goal, plan)
    return runtime, tool


@pytest.mark.asyncio
async def test_runtime_retries_and_waits_at_gate(tmp_path: Path) -> None:
    runtime, tool = _runtime(tmp_path, fail_once=True)
    snapshot = await runtime.run("run_test")
    assert tool.calls == 2
    assert snapshot["run"]["state"] == "WAIT_GATE_2"
    assert snapshot["tasks"][0]["status"] == "succeeded"
    assert snapshot["tasks"][1]["status"] == "waiting_human"


@pytest.mark.asyncio
async def test_resume_does_not_repeat_succeeded_tool(tmp_path: Path) -> None:
    runtime, tool = _runtime(tmp_path)
    await runtime.run("run_test")
    runtime.approve_gate("run_test", approved=True)
    snapshot = await runtime.run("run_test")
    assert snapshot["run"]["state"] == "COMPLETE"
    assert tool.calls == 1


@pytest.mark.asyncio
async def test_auto_mode_skips_gate(tmp_path: Path) -> None:
    runtime, _tool = _runtime(tmp_path, autonomy="auto")
    snapshot = await runtime.run("run_test")
    assert snapshot["run"]["state"] == "COMPLETE"
