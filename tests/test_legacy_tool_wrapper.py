from pathlib import Path

import pytest

from x2video.agent.planner import build_compatibility_plan
from x2video.config.loader import load_config
from x2video.domain.models import ContentGoal
from x2video.tools.base import ToolContext
from x2video.tools.legacy_pipeline import LegacyPipelineTool


@pytest.mark.asyncio
async def test_legacy_stage_is_traceable_without_changing_its_output(tmp_path: Path) -> None:
    output = tmp_path / "legacy-output.json"
    output.write_text("{}\n", encoding="utf-8")

    def legacy_operation(_config, *, date=None):
        return {"path": output, "date": date}

    tool = LegacyPipelineTool(
        name="legacy.fetch",
        stage="fetch",
        config=load_config("x2video.example.toml"),
        operation=legacy_operation,
    )
    result = await tool.execute(
        ToolContext(
            run_id="run_compat",
            task_id="task_fetch",
            work_dir=str(tmp_path),
            payload={"date": "2026-08-29"},
        )
    )

    assert result.summary == "Legacy fetch completed"
    assert result.artifacts[0].path == str(output)
    assert result.payload["date"] == "2026-08-29"


def test_compatibility_plan_preserves_stage_order() -> None:
    goal = ContentGoal(run_id="run_compat", query="legacy", autonomy="auto")
    plan = build_compatibility_plan(goal)
    assert [task.tool_name for task in plan.tasks] == [
        "legacy.fetch",
        "legacy.curate",
        "legacy.card",
        "legacy.script",
        "legacy.render",
    ]
