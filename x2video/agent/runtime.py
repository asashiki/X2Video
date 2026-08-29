"""Bounded task runner with durable state, retry, idempotency, gates, and budgets."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from x2video.domain.models import (
    ContentGoal,
    RunEvent,
    RunPlan,
    RunState,
    TaskStatus,
    ToolCall,
)
from x2video.storage.run_store import RunStore
from x2video.tools.base import ToolContext
from x2video.tools.registry import ToolRegistry


class BudgetExceeded(RuntimeError):
    pass


class AgentRuntime:
    def __init__(self, store: RunStore, registry: ToolRegistry, *, work_dir: str = "work") -> None:
        self.store = store
        self.registry = registry
        self.work_dir = work_dir

    def create(self, goal: ContentGoal, plan: RunPlan) -> str:
        self.store.create_run(goal, plan)
        self.store.append_event(
            RunEvent(
                run_id=goal.run_id,
                event_type="run.created",
                state=RunState.PLAN,
                summary=plan.decision_summary,
                payload={"format": plan.format, "human_gates": plan.human_gates},
            )
        )
        return goal.run_id

    async def run(self, run_id: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        snapshot = self.store.snapshot(run_id)
        if not snapshot:
            raise KeyError(f"Run not found: {run_id}")
        if snapshot["run"]["state"] in {
            RunState.CANCELED.value,
            RunState.FAILED.value,
            RunState.COMPLETE.value,
        }:
            return snapshot
        goal = ContentGoal.model_validate(snapshot["goal"])
        spent = dict(snapshot["run"].get("spent") or {})
        started = time.monotonic()

        while True:
            tasks = self.store.get_tasks(run_id)
            next_task = self._next_task(tasks)
            if next_task is None:
                self.store.set_run_state(run_id, RunState.COMPLETE)
                self._event(run_id, None, "run.completed", RunState.COMPLETE, "Run completed")
                break
            try:
                self._check_budget(goal, spent, started)
            except BudgetExceeded:
                break
            task_id = next_task["task_id"]
            state = RunState(next_task["target_state"])

            if next_task["tool_name"] is None:
                if self._gate_required(goal, state):
                    self.store.set_task_status(task_id, TaskStatus.WAITING_HUMAN)
                    self.store.set_run_state(run_id, state)
                    self._event(
                        run_id,
                        task_id,
                        "gate.waiting",
                        state,
                        f"{state.value} requires approval",
                        TaskStatus.WAITING_HUMAN,
                    )
                    break
                self.store.set_task_status(task_id, TaskStatus.SKIPPED)
                continue

            tool = self.registry.get(next_task["tool_name"])
            attempt = int(next_task["attempt"] or 0) + 1
            self.store.set_run_state(run_id, state)
            self.store.set_task_status(task_id, TaskStatus.RUNNING, attempt=attempt)
            self._event(run_id, task_id, "task.started", state, next_task["task_type"], TaskStatus.RUNNING)
            call_started = time.monotonic()
            idempotency_key = next_task["idempotency_key"]
            try:
                result = await tool.execute(
                    ToolContext(
                        run_id=run_id,
                        task_id=task_id,
                        work_dir=self.work_dir,
                        payload=dict(payload or {}),
                    )
                )
            except Exception as exc:
                latency = int((time.monotonic() - call_started) * 1000)
                self.store.add_tool_call(
                    ToolCall(
                        run_id=run_id,
                        task_id=task_id,
                        tool_name=tool.name,
                        idempotency_key=idempotency_key,
                        status=TaskStatus.FAILED,
                        error=str(exc),
                        attempt=attempt,
                        latency_ms=latency,
                    )
                )
                if attempt < int(next_task["max_attempts"]):
                    self.store.set_task_status(task_id, TaskStatus.PENDING, attempt=attempt, error=str(exc))
                    self._event(run_id, task_id, "task.retry", state, str(exc), TaskStatus.PENDING)
                    continue
                self.store.set_task_status(task_id, TaskStatus.FAILED, attempt=attempt, error=str(exc))
                self.store.set_run_state(run_id, RunState.FAILED, error=str(exc))
                self._event(run_id, task_id, "task.failed", RunState.FAILED, str(exc), TaskStatus.FAILED)
                break

            latency = int((time.monotonic() - call_started) * 1000)
            for artifact in result.artifacts:
                self.store.add_artifact(artifact)
            self.store.add_tool_call(
                ToolCall(
                    run_id=run_id,
                    task_id=task_id,
                    tool_name=tool.name,
                    idempotency_key=idempotency_key,
                    status=TaskStatus.SUCCEEDED,
                    output_summary=result.summary,
                    attempt=attempt,
                    cost_usd=result.cost_usd,
                    latency_ms=latency,
                )
            )
            spent["llm_calls"] = int(spent.get("llm_calls", 0)) + result.llm_calls
            spent["cost_usd"] = float(spent.get("cost_usd", 0)) + result.cost_usd
            spent["runtime_seconds"] = round(time.monotonic() - started, 3)
            self.store.update_spent(run_id, spent)
            self.store.set_task_status(task_id, TaskStatus.SUCCEEDED, attempt=attempt)
            self.store.append_event(
                RunEvent(
                    run_id=run_id,
                    task_id=task_id,
                    event_type="task.succeeded",
                    state=state,
                    status=TaskStatus.SUCCEEDED,
                    summary=result.summary,
                    payload=result.payload,
                    cost_usd=result.cost_usd,
                    latency_ms=latency,
                    output_artifact_ids=[a.artifact_id for a in result.artifacts],
                )
            )

        return self.store.snapshot(run_id) or {}

    def approve_gate(self, run_id: str, *, approved: bool, summary: str = "") -> None:
        tasks = self.store.get_tasks(run_id)
        waiting = next((task for task in tasks if task["status"] == TaskStatus.WAITING_HUMAN.value), None)
        if not waiting:
            raise ValueError("Run has no waiting Gate")
        state = RunState(waiting["target_state"])
        if approved:
            self.store.set_task_status(waiting["task_id"], TaskStatus.SUCCEEDED)
            self._event(run_id, waiting["task_id"], "gate.approved", state, summary or "Gate approved")
        else:
            self.store.set_task_status(waiting["task_id"], TaskStatus.FAILED, error=summary)
            self.store.set_run_state(run_id, RunState.CANCELED, error=summary or "Gate rejected")
            self._event(run_id, waiting["task_id"], "gate.rejected", RunState.CANCELED, summary or "Gate rejected")

    def cancel(self, run_id: str, *, summary: str = "Canceled by user") -> None:
        for task in self.store.get_tasks(run_id):
            if task["status"] in {TaskStatus.PENDING.value, TaskStatus.RUNNING.value}:
                self.store.set_task_status(task["task_id"], TaskStatus.CANCELED)
        self.store.set_run_state(run_id, RunState.CANCELED, error=summary)
        self._event(run_id, None, "run.canceled", RunState.CANCELED, summary)

    def retry(self, run_id: str, *, task_id: str | None = None) -> str:
        tasks = self.store.get_tasks(run_id)
        task = next(
            (
                item
                for item in tasks
                if item["task_id"] == task_id
                or (task_id is None and item["status"] == TaskStatus.FAILED.value)
            ),
            None,
        )
        if not task:
            raise ValueError("No failed task available to retry")
        self.store.set_task_status(task["task_id"], TaskStatus.PENDING, error=None)
        self.store.set_run_state(run_id, RunState(task["target_state"]), error=None)
        self._event(
            run_id,
            task["task_id"],
            "task.retry_requested",
            RunState(task["target_state"]),
            "Retry requested",
            TaskStatus.PENDING,
        )
        return task["task_id"]

    def replay(self, run_id: str) -> dict[str, Any]:
        snapshot = self.store.snapshot(run_id)
        if not snapshot:
            raise KeyError(f"Run not found: {run_id}")
        return {
            "run_id": run_id,
            "state": snapshot["run"]["state"],
            "event_count": len(snapshot["events"]),
            "timeline": [
                {
                    "event_type": event["event_type"],
                    "state": event["state"],
                    "summary": event["summary"],
                    "output_artifact_ids": event["output_artifact_ids"],
                }
                for event in snapshot["events"]
            ],
        }

    @staticmethod
    def _next_task(tasks: list[dict[str, Any]]) -> dict[str, Any] | None:
        succeeded = {
            task["task_id"]
            for task in tasks
            if task["status"] in {TaskStatus.SUCCEEDED.value, TaskStatus.SKIPPED.value}
        }
        for task in tasks:
            if task["status"] in {TaskStatus.PENDING.value, TaskStatus.RUNNING.value}:
                return task
            if task["status"] == TaskStatus.WAITING_HUMAN.value:
                return task
            if task["status"] == TaskStatus.FAILED.value:
                return None
            # Dependencies are encoded in the plan ordering in v0.2.0.
            if task["task_id"] not in succeeded:
                return task
        return None

    @staticmethod
    def _gate_required(goal: ContentGoal, state: RunState) -> bool:
        if goal.autonomy == "auto":
            return False
        if goal.autonomy == "assisted" and state == RunState.WAIT_GATE_1:
            return False
        return state in {RunState.WAIT_GATE_1, RunState.WAIT_GATE_2}

    def _check_budget(self, goal: ContentGoal, spent: dict[str, Any], started: float) -> None:
        reasons = []
        if int(spent.get("llm_calls", 0)) >= goal.budget.max_llm_calls:
            reasons.append("LLM call budget reached")
        if float(spent.get("cost_usd", 0)) >= goal.budget.max_cost_usd:
            reasons.append("cost budget reached")
        if time.monotonic() - started >= goal.budget.max_runtime_seconds:
            reasons.append("runtime budget reached")
        if reasons:
            self.store.set_run_state(goal.run_id, RunState.WAIT_GATE_2, error="; ".join(reasons))
            self._event(
                goal.run_id,
                None,
                "budget.stopped",
                RunState.WAIT_GATE_2,
                "; ".join(reasons),
                TaskStatus.WAITING_HUMAN,
            )
            raise BudgetExceeded("; ".join(reasons))

    def _event(
        self,
        run_id: str,
        task_id: str | None,
        event_type: str,
        state: RunState,
        summary: str,
        status: TaskStatus | None = None,
    ) -> None:
        self.store.append_event(
            RunEvent(
                run_id=run_id,
                task_id=task_id,
                event_type=event_type,
                state=state,
                status=status,
                summary=summary,
                input_hash=hashlib.sha256(summary.encode()).hexdigest(),
            )
        )
