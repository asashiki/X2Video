"""Single application service shared by CLI, API, Worker, and Studio."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from x2video.agent.planner import build_compatibility_plan, build_plan
from x2video.agent.runtime import AgentRuntime
from x2video.auth.oauth import get_status
from x2video.config.schema import X2VideoConfig
from x2video.domain.models import (
    ContentGoal,
    EditorialDecision,
    MemoryCandidate,
    RunEvent,
    RunState,
    TaskStatus,
    UserFeedback,
    new_id,
)
from x2video.storage.run_store import RunStore
from x2video.tools.content import register_content_tools
from x2video.tools.legacy_pipeline import register_legacy_tools
from x2video.tools.registry import ToolRegistry


class ApplicationService:
    def __init__(
        self,
        *,
        work_dir: str = "work",
        db_path: str | None = None,
        config: X2VideoConfig | None = None,
    ) -> None:
        self.work_dir = str(Path(work_dir))
        self.db_path = db_path or str(Path(work_dir) / "x2video-agent.db")
        self.config = config
        self.store = RunStore(self.db_path)
        registry = ToolRegistry()
        register_content_tools(registry, self.store)
        if config is not None:
            register_legacy_tools(registry, config, self.store)
        self.runtime = AgentRuntime(self.store, registry, work_dir=self.work_dir)

    def live_ready(self) -> bool:
        if self.config is None:
            return False
        if self.config.source.provider == "grok":
            return bool(get_status().get("logged_in"))
        return True

    def resolve_mode(self, requested: str | None = None) -> str:
        if requested in {"live", "demo"}:
            if requested == "live" and self.config is None:
                raise ValueError("Live mode needs a loaded x2video.toml")
            return requested
        return "live" if self.live_ready() else "demo"

    def create_run(
        self,
        *,
        query: str,
        autonomy: str = "assisted",
        target_duration_seconds: int = 60,
        preferred_format: str | None = None,
        mode: str | None = None,
    ) -> dict[str, Any]:
        run_id = new_id("run")
        approved_memories = self.store.list_memories(status="approved")
        resolved_mode = self.resolve_mode(mode)
        goal = ContentGoal(
            run_id=run_id,
            query=query,
            autonomy=autonomy,
            target_duration_seconds=target_duration_seconds,
            preferred_format=preferred_format,
            memory_context=[item["content"] for item in approved_memories[:10]],
        )
        if resolved_mode == "live":
            goal.budget.max_runtime_seconds = max(goal.budget.max_runtime_seconds, 1800)
            plan = build_compatibility_plan(goal)
        else:
            plan = build_plan(goal)
        self.runtime.create(goal, plan)
        snapshot = self.get_run(run_id) or {}
        if snapshot.get("run"):
            snapshot["run"]["mode"] = resolved_mode
        return snapshot

    def feedback(
        self,
        run_id: str,
        *,
        category: str,
        comment: str,
        rating: int | None = None,
        target_id: str | None = None,
    ) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError(f"Run not found: {run_id}")
        feedback = UserFeedback(
            run_id=run_id,
            category=category,
            comment=comment.strip(),
            rating=rating,
            target_id=target_id,
        )
        if not feedback.comment:
            raise ValueError("Feedback comment cannot be empty")
        self.store.add_feedback(feedback)
        result = {"feedback_id": feedback.feedback_id, "memory_id": None}
        if category == "preference":
            memory = MemoryCandidate(
                run_id=run_id,
                memory_type="preference",
                content=feedback.comment,
                source_ids=[feedback.feedback_id],
                confidence=0.75 if rating is None else min(0.55 + rating * 0.08, 0.95),
            )
            self.store.add_memory(memory)
            result["memory_id"] = memory.memory_id
        self.store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="feedback.recorded",
                state=RunState(run["state"]),
                summary=f"Recorded {category} feedback",
                payload=result,
            )
        )
        return result

    async def execute(self, run_id: str) -> dict[str, Any]:
        return await self.runtime.run(run_id)

    def execute_sync(self, run_id: str) -> dict[str, Any]:
        return asyncio.run(self.execute(run_id))

    def start_worker(self, run_id: str) -> int:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "x2video.api.worker",
                "--db",
                self.db_path,
                "--work-dir",
                self.work_dir,
                "--run-id",
                run_id,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        run = self.store.get_run(run_id)
        state = RunState(run["state"]) if run else RunState.PLAN
        self.store.append_event(
            RunEvent(
                run_id=run_id,
                event_type="worker.started",
                state=state,
                status=TaskStatus.RUNNING,
                summary="Independent worker started",
                payload={"pid": process.pid},
            )
        )
        return process.pid

    def list_runs(self) -> list[dict[str, Any]]:
        return self.store.list_runs()

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        snapshot = self.store.snapshot(run_id)
        if not snapshot:
            return None
        root = Path(self.work_dir) / "agent_runs" / run_id
        documents = {}
        for name in (
            "curation.json",
            "claim_map.json",
            "script.draft.json",
            "script.final.json",
            "script.review.json",
            "storyboard.json",
            "publish_kit/qc.before.json",
            "publish_kit/qc.after.json",
            "publish_kit/repair.json",
            "publish_kit/render_manifest.json",
        ):
            path = root / name
            if path.exists() and path.stat().st_size < 2_000_000:
                documents[name] = json.loads(path.read_text(encoding="utf-8"))
        publish = root / "publish_kit"
        snapshot["documents"] = documents
        snapshot["media"] = {
            "video": f"/api/runs/{run_id}/media/video" if (publish / "video.mp4").exists() else None,
            "cover": f"/api/runs/{run_id}/media/cover" if (publish / "cover.png").exists() else None,
        }
        live = any(
            str((task.get("tool_name") or "")).startswith("legacy.")
            for task in (snapshot.get("plan") or {}).get("tasks") or []
        )
        snapshot["run"]["mode"] = "live" if live else "demo"
        return snapshot

    def action(self, run_id: str, action: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(payload or {})
        if action == "fork":
            return self.fork(run_id)
        if action == "pause":
            self.runtime.pause(run_id)
        elif action == "resume":
            self.runtime.resume(run_id)
        elif action == "cancel":
            self.runtime.cancel(run_id, summary=payload.get("summary", "Canceled in Studio"))
        elif action == "retry":
            self.runtime.retry(run_id, task_id=payload.get("task_id"))
        elif action in {"approve_gate", "reject_gate"}:
            self.runtime.approve_gate(
                run_id,
                approved=action == "approve_gate",
                summary=payload.get("summary", ""),
            )
        elif action in {"approve_candidate", "reject_candidate", "reorder", "request_research"}:
            self._record_editorial_action(run_id, action, payload)
        elif action in {"lock_segment", "rewrite_segment"}:
            self._edit_script(run_id, action, payload)
        else:
            raise ValueError(f"Unsupported action: {action}")
        return self.get_run(run_id) or {}

    def fork(self, run_id: str) -> dict[str, Any]:
        snapshot = self.get_run(run_id)
        if not snapshot:
            raise KeyError(f"Run not found: {run_id}")
        goal = snapshot["goal"]
        parent_live = any(
            str((task.get("tool_name") or "")).startswith("legacy.")
            for task in (snapshot.get("plan") or {}).get("tasks") or []
        )
        forked = self.create_run(
            query=goal["query"],
            autonomy=goal["autonomy"],
            target_duration_seconds=goal["target_duration_seconds"],
            preferred_format=goal.get("preferred_format"),
            mode="live" if parent_live else "demo",
        )
        child_id = forked["run"]["run_id"]
        self.store.set_parent(child_id, run_id)
        self.store.append_event(
            RunEvent(
                run_id=child_id,
                event_type="run.forked",
                state=RunState.PLAN,
                summary=f"Forked from {run_id}",
                payload={"parent_run_id": run_id},
            )
        )
        return self.get_run(child_id) or {}

    def _record_editorial_action(self, run_id: str, action: str, payload: dict[str, Any]) -> None:
        decisions = [
            EditorialDecision.model_validate(item)
            for item in self.store.payloads("decisions", run_id)
        ]
        candidate_id = payload.get("candidate_id")
        if action in {"approve_candidate", "reject_candidate"}:
            decision = next(
                (item for item in decisions if item.candidate_id == candidate_id),
                None,
            )
            if not decision:
                raise ValueError("Candidate decision not found")
            decision.selected = action == "approve_candidate"
            decision.decision_summary = str(
                payload.get("summary")
                or ("用户在 Gate 1 批准" if decision.selected else "用户在 Gate 1 拒绝")
            )
            self.store.add_decision(decision)
        elif action == "reorder":
            order = [str(item) for item in payload.get("candidate_ids", [])]
            if not order:
                raise ValueError("candidate_ids is required for reorder")
            for decision in decisions:
                if decision.candidate_id in order:
                    decision.rank = order.index(decision.candidate_id) + 1
                    self.store.add_decision(decision)
        run = self.store.get_run(run_id)
        state = RunState(run["state"]) if run else RunState.CURATE
        self.store.append_event(
            RunEvent(
                run_id=run_id,
                event_type=f"curation.{action}",
                state=state,
                summary=payload.get("summary") or action.replace("_", " "),
                payload=payload,
            )
        )

    def _edit_script(self, run_id: str, action: str, payload: dict[str, Any]) -> None:
        path = Path(self.work_dir) / "agent_runs" / run_id / "script.final.json"
        if not path.exists():
            raise ValueError("Run has no editable Script")
        document = json.loads(path.read_text(encoding="utf-8"))
        segment_id = payload.get("segment_id")
        segment = next((item for item in document.get("segments", []) if item["segment_id"] == segment_id), None)
        if not segment:
            raise ValueError("Segment not found")
        if action == "lock_segment":
            segment["locked"] = bool(payload.get("locked", True))
        elif segment.get("locked"):
            raise ValueError("Locked Segment cannot be rewritten")
        else:
            segment["narration"] = str(payload.get("narration") or segment["narration"])
            segment["revision"] = int(segment.get("revision", 1)) + 1
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run = self.store.get_run(run_id)
        self.store.append_event(
            RunEvent(
                run_id=run_id,
                event_type=f"script.{action}",
                state=RunState(run["state"]) if run else RunState.SCRIPT_REVIEW,
                summary=f"{action}: {segment_id}",
                payload={"segment_id": segment_id, "revision": segment.get("revision")},
            )
        )
