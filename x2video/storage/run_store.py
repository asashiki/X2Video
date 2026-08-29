"""Durable Run state, events, evidence, decisions, issues, and feedback."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from x2video.domain.models import (
    Artifact,
    ContentGoal,
    EditorialDecision,
    EvidencePack,
    MemoryCandidate,
    PlanTask,
    QualityIssue,
    RunEvent,
    RunPlan,
    RunState,
    TaskStatus,
    ToolCall,
    UserFeedback,
)
from x2video.security import redact
from x2video.storage.sqlite import connect, migrate


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _dump(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(redact(value), ensure_ascii=False, separators=(",", ":"))


def _row(row: Any) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


class RunStore:
    def __init__(self, path: str | Path = "work/x2video-agent.db") -> None:
        self.path = Path(path)
        with self.transaction() as connection:
            migrate(connection)

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        connection = connect(self.path)
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def create_run(self, goal: ContentGoal, plan: RunPlan) -> None:
        now = _now()
        with self.transaction() as db:
            db.execute(
                """INSERT INTO runs
                (run_id,state,autonomy,format,summary,budget_json,spent_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    goal.run_id,
                    RunState.PLAN.value,
                    goal.autonomy,
                    plan.format,
                    plan.decision_summary,
                    _dump(goal.budget),
                    _dump({"llm_calls": 0, "cost_usd": 0.0, "runtime_seconds": 0}),
                    now,
                    now,
                ),
            )
            db.execute("INSERT INTO goals(run_id,payload_json) VALUES (?,?)", (goal.run_id, _dump(goal)))
            db.execute("INSERT INTO plans(run_id,payload_json) VALUES (?,?)", (goal.run_id, _dump(plan)))
            for task in plan.tasks:
                self._insert_task(db, goal.run_id, task)

    @staticmethod
    def _insert_task(db: Any, run_id: str, task: PlanTask) -> None:
        db.execute(
            """INSERT INTO tasks
            (task_id,run_id,task_type,target_state,tool_name,status,max_attempts,idempotency_key)
            VALUES (?,?,?,?,?,?,?,?)""",
            (
                task.task_id,
                run_id,
                task.task_type,
                task.target_state.value,
                task.tool_name,
                TaskStatus.PENDING.value,
                task.max_attempts,
                f"{run_id}:{task.task_id}:{task.tool_name or task.task_type}",
            ),
        )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.transaction() as db:
            run = _row(db.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone())
            if run:
                for key in ("budget_json", "spent_json"):
                    run[key.removesuffix("_json")] = json.loads(run.pop(key))
            return run

    def list_runs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self.transaction() as db:
            rows = db.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def set_run_state(self, run_id: str, state: RunState, *, error: str | None = None) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE runs SET state=?,error=?,updated_at=? WHERE run_id=?",
                (state.value, redact(error), _now(), run_id),
            )

    def update_spent(self, run_id: str, spent: dict[str, Any]) -> None:
        with self.transaction() as db:
            db.execute(
                "UPDATE runs SET spent_json=?,updated_at=? WHERE run_id=?",
                (_dump(spent), _now(), run_id),
            )

    def get_tasks(self, run_id: str) -> list[dict[str, Any]]:
        with self.transaction() as db:
            rows = db.execute(
                "SELECT * FROM tasks WHERE run_id=? ORDER BY rowid", (run_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def set_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        *,
        attempt: int | None = None,
        error: str | None = None,
    ) -> None:
        started = _now() if status == TaskStatus.RUNNING else None
        finished = _now() if status in {
            TaskStatus.SUCCEEDED,
            TaskStatus.FAILED,
            TaskStatus.SKIPPED,
            TaskStatus.CANCELED,
        } else None
        fields = ["status=?", "error=?"]
        values: list[Any] = [status.value, redact(error)]
        if started:
            fields.append("started_at=COALESCE(started_at, ?)")
            values.append(started)
        if finished:
            fields.append("finished_at=?")
            values.append(finished)
        if attempt is not None:
            fields.append("attempt=?")
            values.append(attempt)
        values.append(task_id)
        with self.transaction() as db:
            db.execute(f"UPDATE tasks SET {','.join(fields)} WHERE task_id=?", values)

    def append_event(self, event: RunEvent) -> None:
        with self.transaction() as db:
            db.execute(
                """INSERT INTO events
                (event_id,run_id,task_id,created_at,event_type,state,status,summary,payload_json,
                 cost_usd,latency_ms,provider,input_hash,output_artifact_ids_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event.event_id,
                    event.run_id,
                    event.task_id,
                    event.created_at.isoformat(),
                    event.event_type,
                    event.state.value,
                    event.status.value if event.status else None,
                    redact(event.summary),
                    _dump(event.payload),
                    event.cost_usd,
                    event.latency_ms,
                    event.provider,
                    event.input_hash,
                    _dump(event.output_artifact_ids),
                ),
            )

    def list_events(self, run_id: str, *, after: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM events WHERE run_id=?"
        values: list[Any] = [run_id]
        if after:
            query += " AND created_at>?"
            values.append(after)
        query += " ORDER BY created_at,event_id"
        with self.transaction() as db:
            rows = db.execute(query, values).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            item["output_artifact_ids"] = json.loads(item.pop("output_artifact_ids_json"))
            items.append(item)
        return items

    def add_tool_call(self, call: ToolCall) -> None:
        with self.transaction() as db:
            db.execute(
                """INSERT OR REPLACE INTO tool_calls
                (tool_call_id,run_id,task_id,tool_name,idempotency_key,status,attempt,payload_json,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    call.tool_call_id,
                    call.run_id,
                    call.task_id,
                    call.tool_name,
                    call.idempotency_key,
                    call.status.value,
                    call.attempt,
                    _dump(call),
                    call.created_at.isoformat(),
                ),
            )

    def add_artifact(self, artifact: Artifact) -> None:
        with self.transaction() as db:
            db.execute(
                """INSERT OR IGNORE INTO artifacts
                (artifact_id,run_id,kind,path,input_hash,payload_json,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    artifact.artifact_id,
                    artifact.run_id,
                    artifact.kind,
                    artifact.path,
                    artifact.input_hash,
                    _dump(artifact),
                    artifact.created_at.isoformat(),
                ),
            )

    def add_evidence(self, pack: EvidencePack) -> None:
        self._add_payload(
            "evidence",
            ("evidence_pack_id", "run_id", "candidate_id", "payload_json", "created_at"),
            (pack.evidence_pack_id, pack.run_id, pack.candidate_id, _dump(pack), pack.created_at.isoformat()),
        )

    def add_decision(self, decision: EditorialDecision) -> None:
        self._add_payload(
            "decisions",
            ("decision_id", "run_id", "candidate_id", "selected", "payload_json", "created_at"),
            (
                decision.decision_id,
                decision.run_id,
                decision.candidate_id,
                int(decision.selected),
                _dump(decision),
                decision.created_at.isoformat(),
            ),
        )

    def add_quality_issue(self, issue: QualityIssue) -> None:
        self._add_payload(
            "quality_issues",
            ("issue_id", "run_id", "severity", "resolved", "payload_json", "created_at"),
            (
                issue.issue_id,
                issue.run_id,
                issue.severity,
                int(issue.resolved),
                _dump(issue),
                issue.created_at.isoformat(),
            ),
        )

    def add_feedback(self, feedback: UserFeedback) -> None:
        self._add_payload(
            "feedback",
            ("feedback_id", "run_id", "payload_json", "created_at"),
            (feedback.feedback_id, feedback.run_id, _dump(feedback), feedback.created_at.isoformat()),
        )

    def add_memory(self, memory: MemoryCandidate) -> None:
        with self.transaction() as db:
            db.execute(
                """INSERT INTO memories
                (memory_id,run_id,memory_type,status,content,payload_json,created_at)
                VALUES (?,?,?,?,?,?,?)""",
                (
                    memory.memory_id,
                    memory.run_id,
                    memory.memory_type,
                    memory.status,
                    redact(memory.content),
                    _dump(memory),
                    memory.created_at.isoformat(),
                ),
            )
            db.execute(
                "INSERT INTO memories_fts(memory_id,content) VALUES (?,?)",
                (memory.memory_id, redact(memory.content)),
            )

    def _add_payload(self, table: str, columns: tuple[str, ...], values: tuple[Any, ...]) -> None:
        placeholders = ",".join("?" for _ in values)
        with self.transaction() as db:
            db.execute(
                f"INSERT OR REPLACE INTO {table}({','.join(columns)}) VALUES ({placeholders})",
                values,
            )

    def payloads(self, table: str, run_id: str) -> list[dict[str, Any]]:
        allowed = {"evidence", "decisions", "quality_issues", "feedback", "memories", "artifacts"}
        if table not in allowed:
            raise ValueError(f"Unsupported payload table: {table}")
        with self.transaction() as db:
            rows = db.execute(
                f"SELECT payload_json FROM {table} WHERE run_id=? ORDER BY created_at", (run_id,)
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def snapshot(self, run_id: str) -> dict[str, Any] | None:
        run = self.get_run(run_id)
        if not run:
            return None
        with self.transaction() as db:
            goal_row = db.execute("SELECT payload_json FROM goals WHERE run_id=?", (run_id,)).fetchone()
            plan_row = db.execute("SELECT payload_json FROM plans WHERE run_id=?", (run_id,)).fetchone()
        return {
            "run": run,
            "goal": json.loads(goal_row[0]) if goal_row else None,
            "plan": json.loads(plan_row[0]) if plan_row else None,
            "tasks": self.get_tasks(run_id),
            "events": self.list_events(run_id),
            "evidence": self.payloads("evidence", run_id),
            "decisions": self.payloads("decisions", run_id),
            "quality_issues": self.payloads("quality_issues", run_id),
            "artifacts": self.payloads("artifacts", run_id),
        }
