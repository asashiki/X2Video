"""Versioned contracts shared by the Agent Kernel, CLI, API, and Studio."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class RunState(StrEnum):
    INIT = "INIT"
    PLAN = "PLAN"
    DISCOVER = "DISCOVER"
    RESEARCH = "RESEARCH"
    CURATE = "CURATE"
    WAIT_GATE_1 = "WAIT_GATE_1"
    SCRIPT = "SCRIPT"
    SCRIPT_REVIEW = "SCRIPT_REVIEW"
    STORYBOARD = "STORYBOARD"
    PRODUCE = "PRODUCE"
    QUALITY_REVIEW = "QUALITY_REVIEW"
    REPAIR = "REPAIR"
    WAIT_GATE_2 = "WAIT_GATE_2"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELED = "canceled"


class VersionedModel(BaseModel):
    schema_version: str = "1.0"
    run_id: str
    created_at: datetime = Field(default_factory=utc_now)
    producer_version: str = "x2video/0.2"
    input_hash: str = ""


class RunBudget(BaseModel):
    max_llm_calls: int = 20
    max_cost_usd: float = 2.0
    max_runtime_seconds: int = 900
    max_script_revisions: int = 2
    max_repairs: int = 2
    max_candidates: int = 50


class ContentGoal(VersionedModel):
    goal_id: str = Field(default_factory=lambda: new_id("goal"))
    query: str
    domain: str = "AI/科技"
    audience: str = "普通中文用户"
    platforms: list[str] = Field(default_factory=lambda: ["抖音", "B站"])
    target_duration_seconds: int = 60
    freshness_hours: int = 24
    tone: str = "克制、清晰、有吸引力"
    preferred_format: Literal["news_recap", "single_explainer", "thread_story"] | None = None
    autonomy: Literal["supervised", "assisted", "auto"] = "assisted"
    risk_tolerance: Literal["low", "medium", "high"] = "low"
    memory_context: list[str] = Field(default_factory=list)
    budget: RunBudget = Field(default_factory=RunBudget)


class PlanTask(BaseModel):
    task_id: str = Field(default_factory=lambda: new_id("task"))
    task_type: str
    target_state: RunState
    tool_name: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    exit_conditions: list[str] = Field(default_factory=list)
    max_attempts: int = 2
    estimated_cost_usd: float | None = None
    human_gate: bool = False


class RunPlan(VersionedModel):
    format: Literal["news_recap", "single_explainer", "thread_story"]
    tasks: list[PlanTask]
    decision_summary: str
    human_gates: list[str] = Field(default_factory=list)


class RunEvent(VersionedModel):
    event_id: str = Field(default_factory=lambda: new_id("event"))
    task_id: str | None = None
    event_type: str
    state: RunState
    status: TaskStatus | None = None
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: int = 0
    provider: str | None = None
    output_artifact_ids: list[str] = Field(default_factory=list)


class ToolCall(VersionedModel):
    tool_call_id: str = Field(default_factory=lambda: new_id("tool"))
    task_id: str
    tool_name: str
    idempotency_key: str
    status: TaskStatus
    input_summary: str = ""
    output_summary: str = ""
    error: str | None = None
    attempt: int = 1
    cost_usd: float = 0.0
    latency_ms: int = 0


class Artifact(VersionedModel):
    artifact_id: str = Field(default_factory=lambda: new_id("artifact"))
    kind: str
    path: str
    mime_type: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class EvidenceSource(VersionedModel):
    source_id: str = Field(default_factory=lambda: new_id("source"))
    url: str
    source_type: str
    title: str | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=utc_now)
    author: str | None = None
    excerpt: str
    trust_signals: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    claim_id: str = Field(default_factory=lambda: new_id("claim"))
    normalized_claim: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    contradicting_source_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class EvidencePack(VersionedModel):
    evidence_pack_id: str = Field(default_factory=lambda: new_id("evidence"))
    candidate_id: str
    thread_context: list[str] = Field(default_factory=list)
    sources: list[EvidenceSource] = Field(default_factory=list)
    claims: list[ClaimEvidence] = Field(default_factory=list)
    freshness_score: float = 0.0
    context_completeness: float = 0.0
    overall_confidence: float = 0.0
    risk_flags: list[str] = Field(default_factory=list)


class EditorialDecision(VersionedModel):
    decision_id: str = Field(default_factory=lambda: new_id("decision"))
    candidate_id: str
    selected: bool
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    decision_summary: str
    evidence_ids: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    rejected_because: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    rank: int | None = None


class ScriptIssue(VersionedModel):
    issue_id: str = Field(default_factory=lambda: new_id("script_issue"))
    segment_id: str
    category: str
    severity: Literal["info", "warning", "error", "blocker"]
    message: str
    patch_instruction: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    resolved: bool = False


class GroundedSegment(BaseModel):
    segment_id: str = Field(default_factory=lambda: new_id("segment"))
    pick_id: str
    narration: str
    evidence_ids: list[str] = Field(default_factory=list)
    locked: bool = False
    revision: int = 1


class GroundedScript(VersionedModel):
    script_id: str = Field(default_factory=lambda: new_id("script"))
    hook: str
    segments: list[GroundedSegment] = Field(default_factory=list)
    outro: str = ""
    title_suggestions: list[str] = Field(default_factory=list)
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class ClaimEvidenceMap(VersionedModel):
    segment_id: str
    claim_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    coverage: float = 0.0


class ScenePlan(BaseModel):
    scene_id: str = Field(default_factory=lambda: new_id("scene"))
    pick_id: str | None = None
    narration_ref: str
    visual_source_ids: list[str] = Field(default_factory=list)
    template: str
    duration_seconds: float
    crop_strategy: str = "contain"
    motion: str = "subtle_push"
    overlay_text: list[str] = Field(default_factory=list)
    safe_area_profile: str = "vertical_standard"
    transition: str = "cut"
    attribution: str | None = None


class Storyboard(VersionedModel):
    storyboard_id: str = Field(default_factory=lambda: new_id("storyboard"))
    template: Literal["news_recap", "single_explainer", "thread_story"]
    scenes: list[ScenePlan] = Field(default_factory=list)
    expected_duration_seconds: float = 0.0


class QualityIssue(VersionedModel):
    issue_id: str = Field(default_factory=lambda: new_id("quality"))
    code: str
    category: Literal["fact", "script", "visual", "audio", "subtitle", "risk"]
    severity: Literal["info", "warning", "error", "blocker"]
    scene_id: str | None = None
    timestamp_seconds: float | None = None
    evidence: list[str] = Field(default_factory=list)
    description: str
    auto_fixable: bool = False
    proposed_patch: dict[str, Any] | None = None
    resolved: bool = False


class RepairAction(VersionedModel):
    repair_id: str = Field(default_factory=lambda: new_id("repair"))
    issue_id: str
    handler: str
    invalidated_artifact_ids: list[str] = Field(default_factory=list)
    before_artifact_ids: list[str] = Field(default_factory=list)
    after_artifact_ids: list[str] = Field(default_factory=list)
    summary: str
    attempt: int = 1
    succeeded: bool = False


class UserFeedback(VersionedModel):
    feedback_id: str = Field(default_factory=lambda: new_id("feedback"))
    category: Literal["selection", "script", "visual", "quality", "preference", "other"]
    target_id: str | None = None
    rating: int | None = None
    comment: str = ""


class MemoryCandidate(VersionedModel):
    memory_id: str = Field(default_factory=lambda: new_id("memory"))
    memory_type: Literal["preference", "production", "performance"]
    content: str
    source_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    expires_at: datetime | None = None


class EvalCase(VersionedModel):
    case_id: str
    name: str
    category: str
    fixture_path: str
    expected: dict[str, Any] = Field(default_factory=dict)


class EvalResult(VersionedModel):
    eval_result_id: str = Field(default_factory=lambda: new_id("eval"))
    case_id: str
    passed: bool
    metrics: dict[str, float] = Field(default_factory=dict)
    issues: list[str] = Field(default_factory=list)
    baseline_id: str | None = None
