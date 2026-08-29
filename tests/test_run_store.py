from pathlib import Path

from x2video.domain.models import (
    ContentGoal,
    PlanTask,
    RunEvent,
    RunPlan,
    RunState,
    TaskStatus,
)
from x2video.storage.run_store import RunStore


def _models(run_id: str) -> tuple[ContentGoal, RunPlan]:
    goal = ContentGoal(run_id=run_id, query="今日 AI 新闻")
    task = PlanTask(task_type="discover", target_state=RunState.DISCOVER, tool_name="fetch")
    plan = RunPlan(
        run_id=run_id,
        format="news_recap",
        tasks=[task],
        decision_summary="按新闻合集处理",
    )
    return goal, plan


def test_run_store_roundtrip_and_redaction(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "agent.db")
    goal, plan = _models("run_1")
    store.create_run(goal, plan)
    task_id = plan.tasks[0].task_id
    store.set_task_status(task_id, TaskStatus.RUNNING, attempt=1)
    store.append_event(
        RunEvent(
            run_id="run_1",
            task_id=task_id,
            event_type="task.started",
            state=RunState.DISCOVER,
            status=TaskStatus.RUNNING,
            summary="Authorization: Bearer abcdefghijklmnop",
            payload={"api_key": "secret", "safe": "ok"},
        )
    )
    snapshot = store.snapshot("run_1")
    assert snapshot is not None
    assert snapshot["run"]["state"] == "PLAN"
    assert snapshot["tasks"][0]["status"] == "running"
    assert "abcdefghijklmnop" not in snapshot["events"][0]["summary"]
    assert snapshot["events"][0]["payload"]["api_key"] == "[REDACTED]"


def test_run_store_state_survives_new_instance(tmp_path: Path) -> None:
    path = tmp_path / "agent.db"
    first = RunStore(path)
    goal, plan = _models("run_resume")
    first.create_run(goal, plan)
    first.set_run_state("run_resume", RunState.RESEARCH)
    second = RunStore(path)
    assert second.get_run("run_resume")["state"] == "RESEARCH"
