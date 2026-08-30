"""Deterministic plan skeleton selected from a versioned Content Goal."""

from __future__ import annotations

from x2video.domain.models import ContentGoal, PlanTask, RunPlan, RunState


def select_format(goal: ContentGoal) -> str:
    if goal.preferred_format:
        return goal.preferred_format
    query = goal.query.lower()
    if "thread" in query or "长推" in query or "串" in query:
        return "thread_story"
    if any(token in query for token in ("深挖", "解释", "单条", "一个")):
        return "single_explainer"
    return "news_recap"


def build_plan(goal: ContentGoal) -> RunPlan:
    format_name = select_format(goal)
    definitions = [
        ("discover", RunState.DISCOVER, "content.discover", False),
        ("research", RunState.RESEARCH, "evidence.research", False),
        ("curate", RunState.CURATE, "portfolio.curate", False),
        ("gate_1", RunState.WAIT_GATE_1, None, True),
        ("script", RunState.SCRIPT, "script.compose", False),
        ("script_review", RunState.SCRIPT_REVIEW, "script.review", False),
        ("storyboard", RunState.STORYBOARD, "visual.storyboard", False),
        ("produce", RunState.PRODUCE, "producer.render", False),
        ("quality_review", RunState.QUALITY_REVIEW, "quality.review", False),
        ("repair", RunState.REPAIR, "quality.repair", False),
        ("gate_2", RunState.WAIT_GATE_2, None, True),
    ]
    tasks: list[PlanTask] = []
    previous: str | None = None
    for task_type, state, tool, gate in definitions:
        task = PlanTask(
            task_type=task_type,
            target_state=state,
            tool_name=tool,
            depends_on=[previous] if previous else [],
            exit_conditions=["versioned output validates", "budget remains"],
            max_attempts=2,
            human_gate=gate,
        )
        tasks.append(task)
        previous = task.task_id
    gates = [] if goal.autonomy == "auto" else ["Gate 1", "Gate 2"]
    memory_note = f"；应用 {len(goal.memory_context)} 条已批准偏好" if goal.memory_context else ""
    return RunPlan(
        run_id=goal.run_id,
        format=format_name,
        tasks=tasks,
        decision_summary=(
            f"采用 {format_name}；{goal.autonomy} 自治等级；"
            f"{goal.target_duration_seconds} 秒目标，最多 {goal.budget.max_candidates} 个 Candidate{memory_note}。"
        ),
        human_gates=gates,
    )


def build_compatibility_plan(goal: ContentGoal) -> RunPlan:
    stages = [
        ("fetch", RunState.DISCOVER),
        ("curate", RunState.CURATE),
        ("card", RunState.STORYBOARD),
        ("script", RunState.SCRIPT),
        ("render", RunState.PRODUCE),
    ]
    tasks: list[PlanTask] = []
    previous: str | None = None
    for stage, state in stages:
        task = PlanTask(
            task_type=f"legacy_{stage}",
            target_state=state,
            tool_name=f"legacy.{stage}",
            depends_on=[previous] if previous else [],
            max_attempts=1,
        )
        tasks.append(task)
        previous = task.task_id
    return RunPlan(
        run_id=goal.run_id,
        format="news_recap",
        tasks=tasks,
        decision_summary="Compatibility Plan：由 Agent Kernel 追踪并调用 v0.1 pipeline Tools。",
        human_gates=[] if goal.autonomy == "auto" else ["Gate 1", "Gate 2"],
    )
