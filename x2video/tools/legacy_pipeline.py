"""Tool wrappers around the stable v0.1 pipeline stages."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from x2video.config.schema import X2VideoConfig
from x2video.domain.models import (
    Artifact,
    ClaimEvidence,
    EditorialDecision,
    EvidencePack,
    EvidenceSource,
    GroundedScript,
    GroundedSegment,
    ScenePlan,
    Storyboard,
)
from x2video.pipeline.card import run_card
from x2video.pipeline.curate import run_curate
from x2video.pipeline.fetch import run_fetch
from x2video.pipeline.io import load_candidates, load_picks, load_script
from x2video.pipeline.render import run_render
from x2video.pipeline.script import run_script
from x2video.pipeline.workdir import resolve_run_dir, today_stamp
from x2video.storage.run_store import RunStore
from x2video.tools.base import AgentTool, ToolContext, ToolResult
from x2video.util import picks_for_duration, search_terms


class LegacyPipelineTool(AgentTool):
    def __init__(
        self,
        *,
        name: str,
        stage: str,
        config: X2VideoConfig,
        operation: Callable[..., Any],
        is_async: bool = False,
        store: RunStore | None = None,
    ) -> None:
        self.name = name
        self.stage = stage
        self.config = config
        self.operation = operation
        self.is_async = is_async
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        date = str(context.payload.get("date") or today_stamp())
        run_cfg = _isolate_config(self.config, context)
        kwargs = dict(context.payload.get("stage_options") or {})
        kwargs["date"] = date
        goal = {}
        if self.store:
            snapshot = self.store.snapshot(context.run_id) or {}
            goal = snapshot.get("goal") or {}
        query = str(goal.get("query") or "")
        seconds = int(goal.get("target_duration_seconds") or 60)
        def inject(name: str, value: Any) -> None:
            if _accepts_kwarg(self.operation, name):
                kwargs.setdefault(name, value)

        if self.stage == "fetch":
            inject("keywords", search_terms(query, list(run_cfg.domain_keywords)))
        if self.stage == "curate":
            inject("auto", True)
            inject("top_n", picks_for_duration(seconds, run_cfg.curation.top_n))
            if query:
                inject("theme", query)
        if self.stage == "script":
            inject("target_duration_seconds", seconds)
        if self.is_async:
            result = await self.operation(run_cfg, **kwargs)
        else:
            result = await asyncio.to_thread(self.operation, run_cfg, **kwargs)
        _sync_ledger(self.config, run_cfg)
        studio_root = Path(context.work_dir) / "agent_runs" / context.run_id
        project_legacy_outputs(
            stage=self.stage,
            run_id=context.run_id,
            config=run_cfg,
            date=date,
            studio_root=studio_root,
            store=self.store,
            result=result if isinstance(result, dict) else {},
        )
        artifacts = _result_artifacts(context.run_id, self.stage, result)
        publish = studio_root / "publish_kit"
        for extra in (publish / "video.mp4", publish / "cover.png"):
            if extra.exists():
                artifacts.append(
                    Artifact(
                        run_id=context.run_id,
                        kind=extra.stem,
                        path=str(extra),
                        input_hash=hashlib.sha256(extra.read_bytes()).hexdigest(),
                    )
                )
        return ToolResult(
            summary=_stage_summary(self.stage, result),
            artifacts=artifacts,
            payload=_summarize(result),
        )


def register_legacy_tools(registry: Any, config: X2VideoConfig, store: RunStore | None = None) -> None:
    definitions: list[tuple[str, str, Callable[..., Any], bool]] = [
        ("legacy.fetch", "fetch", run_fetch, False),
        ("legacy.curate", "curate", run_curate, True),
        ("legacy.card", "card", run_card, False),
        ("legacy.script", "script", run_script, True),
        ("legacy.render", "render", run_render, True),
    ]
    for name, stage, operation, is_async in definitions:
        registry.register(
            LegacyPipelineTool(
                name=name,
                stage=stage,
                config=config,
                operation=operation,
                is_async=is_async,
                store=store,
            )
        )


def _accepts_kwarg(operation: Callable[..., Any], name: str) -> bool:
    """Return True when ``operation`` declares ``name`` (or accepts **kwargs)."""
    try:
        params = inspect.signature(operation).parameters
    except (TypeError, ValueError):
        return False
    if name in params:
        return True
    return any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())


def _isolate_config(config: X2VideoConfig, context: ToolContext) -> X2VideoConfig:
    isolated = Path(context.work_dir) / "agent_runs" / context.run_id / "pipeline"
    isolated.mkdir(parents=True, exist_ok=True)
    run_cfg = config.model_copy(deep=True)
    run_cfg.work_dir = str(isolated)
    run_cfg.final_dir = str(Path(context.work_dir) / "agent_runs" / context.run_id / "final")
    shared_ledger = Path(config.work_dir) / "ledger.json"
    local_ledger = isolated / "ledger.json"
    if shared_ledger.exists() and not local_ledger.exists():
        shutil.copy2(shared_ledger, local_ledger)
    return run_cfg


def _sync_ledger(shared: X2VideoConfig, isolated: X2VideoConfig) -> None:
    local = Path(isolated.work_dir) / "ledger.json"
    if local.exists():
        dest = Path(shared.work_dir)
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local, dest / "ledger.json")


def project_legacy_outputs(
    *,
    stage: str,
    run_id: str,
    config: X2VideoConfig,
    date: str,
    studio_root: Path,
    store: RunStore | None,
    result: dict[str, Any],
) -> None:
    """Copy pipeline artifacts into the Studio Run layout and evidence tables."""
    studio_root.mkdir(parents=True, exist_ok=True)
    day = resolve_run_dir(config.work_dir, date)
    if stage == "fetch":
        src = day / "candidates.json"
        if src.exists():
            shutil.copy2(src, studio_root / "candidates.json")
            _project_candidates(run_id, src, store)
    elif stage == "curate":
        src = day / "picks.json"
        if src.exists():
            shutil.copy2(src, studio_root / "picks.json")
            _project_picks(run_id, day, store)
        scored = day / "scored.json"
        if scored.exists():
            shutil.copy2(scored, studio_root / "scored.json")
        notes = day / "candidates.md"
        if notes.exists():
            shutil.copy2(notes, studio_root / "candidates.md")
    elif stage == "card":
        cards = day / "cards"
        if cards.exists():
            dest = studio_root / "cards"
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(cards, dest)
    elif stage == "script":
        src = day / "script.json"
        if src.exists():
            shutil.copy2(src, studio_root / "script.json")
            _project_script(run_id, src, studio_root)
    elif stage == "render":
        _project_publish_kit(run_id, day, studio_root, result)


def _project_candidates(run_id: str, path: Path, store: RunStore | None) -> None:
    if store is None:
        return
    _meta, candidates = load_candidates(path)
    for candidate in candidates:
        excerpt = (candidate.translation if hasattr(candidate, "translation") else "") or candidate.text
        pack = EvidencePack(
            evidence_pack_id=f"evidence_{run_id}_{candidate.id}",
            run_id=run_id,
            candidate_id=candidate.id,
            sources=[
                EvidenceSource(
                    run_id=run_id,
                    source_id=f"source_{candidate.id}",
                    url=candidate.url or f"https://x.com/i/web/status/{candidate.id}",
                    source_type="x_post",
                    title=f"@{candidate.author_username}" if candidate.author_username else candidate.author_name,
                    excerpt=excerpt[:280],
                    author=candidate.author_name or candidate.author_username,
                    trust_signals=["x_post"],
                )
            ],
            claims=[
                ClaimEvidence(
                    claim_id=f"claim_{candidate.id}",
                    normalized_claim=candidate.text[:180],
                    supporting_source_ids=[f"source_{candidate.id}"],
                    confidence=0.7,
                )
            ],
            overall_confidence=0.7,
            freshness_score=0.8,
            context_completeness=0.6 if candidate.text else 0.2,
        )
        store.add_evidence(pack)
        store.add_decision(
            EditorialDecision(
                decision_id=f"decision_{run_id}_{candidate.id}",
                run_id=run_id,
                candidate_id=candidate.id,
                selected=False,
                confidence=0.5,
                decision_summary=candidate.text[:80] or candidate.id,
                evidence_ids=[pack.evidence_pack_id],
            )
        )


def _project_picks(run_id: str, day: Path, store: RunStore | None) -> None:
    if store is None:
        return
    _meta, picks = load_picks(day / "picks.json")
    pick_ids = {item.id for item in picks}
    _cmeta, candidates = load_candidates(day / "candidates.json") if (day / "candidates.json").exists() else ({}, [])
    ranked = {item.id: index + 1 for index, item in enumerate(picks)}
    for candidate in candidates or picks:
        selected = candidate.id in pick_ids
        pick = next((item for item in picks if item.id == candidate.id), None)
        summary = (pick.reason if pick and pick.reason else candidate.text)[:120]
        store.add_decision(
            EditorialDecision(
                decision_id=f"decision_{run_id}_{candidate.id}",
                run_id=run_id,
                candidate_id=candidate.id,
                selected=selected,
                confidence=min(max((pick.score / 10) if pick and pick.score else 0.7, 0.1), 0.99),
                decision_summary=summary or ("入选 Digest" if selected else "未入选"),
                evidence_ids=[f"evidence_{run_id}_{candidate.id}"],
                rank=ranked.get(candidate.id),
                rejected_because=[] if selected else ["未进入 top picks"],
            )
        )


def _project_script(run_id: str, src: Path, studio_root: Path) -> None:
    digest = load_script(src)
    grounded = GroundedScript(
        run_id=run_id,
        hook=digest.hook,
        outro=digest.outro,
        title_suggestions=digest.title_suggestions,
        description=digest.description,
        tags=digest.tags,
        segments=[
            GroundedSegment(
                segment_id=f"seg_{index:02d}",
                pick_id=segment.pick_id,
                narration=segment.narration,
                evidence_ids=[f"evidence_{run_id}_{segment.pick_id}"],
            )
            for index, segment in enumerate(digest.segments, start=1)
        ],
    )
    _write_json(studio_root / "script.final.json", grounded)
    _write_json(studio_root / "script.draft.json", grounded)
    _write_json(studio_root / "script.review.json", {"issues": [], "diffs": [], "rounds": 0})
    scenes = [
        ScenePlan(
            pick_id=segment.pick_id,
            narration_ref=segment.segment_id,
            visual_source_ids=segment.evidence_ids,
            template="tweet_card",
            duration_seconds=8.0,
            overlay_text=[segment.narration[:24]],
            attribution=f"source:{segment.pick_id}",
        )
        for segment in grounded.segments
    ]
    if digest.hook:
        scenes.insert(
            0,
            ScenePlan(
                pick_id=None,
                narration_ref="hook",
                template="opener",
                duration_seconds=4.0,
                overlay_text=[digest.hook[:24]],
            ),
        )
    storyboard = Storyboard(
        run_id=run_id,
        template="news_recap",
        scenes=scenes,
        expected_duration_seconds=sum(scene.duration_seconds for scene in scenes),
    )
    _write_json(studio_root / "storyboard.json", storyboard)


def _project_publish_kit(run_id: str, day: Path, studio_root: Path, result: dict[str, Any]) -> None:
    publish = studio_root / "publish_kit"
    publish.mkdir(parents=True, exist_ok=True)
    pointer = day / "publish_kit.json"
    payload = result
    if pointer.exists():
        payload = {**json.loads(pointer.read_text(encoding="utf-8")), **payload}
        shutil.copy2(pointer, studio_root / "publish_kit.json")
    video = Path(str(payload.get("video") or ""))
    cover = Path(str(payload.get("cover") or ""))
    if video.exists():
        shutil.copy2(video, publish / "video.mp4")
    if cover.exists():
        shutil.copy2(cover, publish / "cover.png")
    qc = payload.get("qc") if isinstance(payload.get("qc"), dict) else {}
    if not qc:
        kit_qc = Path(str(payload.get("kit_dir") or "")) / "qc.json"
        if kit_qc.exists():
            qc = json.loads(kit_qc.read_text(encoding="utf-8"))
    _write_json(
        publish / "qc.after.json",
        {
            "schema_version": "1.0",
            "ok": bool(qc.get("ok", False)) if qc else (publish / "video.mp4").exists(),
            "checks": qc.get("checks") or {"video_exists": (publish / "video.mp4").exists()},
            "errors": qc.get("errors") or [],
            "warnings": qc.get("warnings") or [],
            "unresolved": qc.get("errors") or [],
        },
    )
    duration = None
    video_path = publish / "video.mp4"
    if video_path.exists():
        try:
            from x2video.tools.content import _probe_duration

            duration = _probe_duration(video_path)
        except Exception:
            duration = None
    _write_json(
        publish / "qc.before.json",
        {
            "schema_version": "1.0",
            "duration_seconds": duration,
            "checks": qc.get("checks") or {},
            "issues": [],
        },
    )
    src_md = Path(str(payload.get("publish_md") or ""))
    if src_md.exists():
        shutil.copy2(src_md, publish / "publish.md")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _stage_summary(stage: str, result: Any) -> str:
    if not isinstance(result, dict):
        return f"原管线 {stage} 完成"
    if stage == "fetch":
        return f"从 X 抓到 {result.get('kept', result.get('fetched', 0))} 条 Candidate"
    if stage == "curate":
        picks = result.get("picks")
        count = len(picks) if isinstance(picks, list) else 0
        return f"选出 {count} 条 Pick"
    if stage == "card":
        return f"已渲染 {result.get('count', 0)} 张推文卡片"
    if stage == "script":
        return f"已生成 {result.get('n', 0)} 段中文口播"
    if stage == "render":
        return "已合成竖屏速览成片"
    return f"原管线 {stage} 完成"


def _result_artifacts(run_id: str, stage: str, result: Any) -> list[Artifact]:
    if not isinstance(result, dict):
        return []
    paths: list[Path] = []
    for value in result.values():
        if isinstance(value, Path):
            paths.append(value)
        elif isinstance(value, str) and ("/" in value or "\\" in value):
            path = Path(value)
            if path.exists() and path.is_file():
                paths.append(path)
    artifacts = []
    for path in paths:
        digest = hashlib.sha256(str(path).encode()).hexdigest()
        artifacts.append(
            Artifact(
                run_id=run_id,
                kind=f"legacy.{stage}",
                path=str(path),
                input_hash=digest,
            )
        )
    return artifacts


def _summarize(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {"result_type": type(result).__name__}
    safe: dict[str, Any] = {}
    for key, value in result.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        elif isinstance(value, Path):
            safe[key] = str(value)
        elif isinstance(value, list):
            safe[key] = len(value)
    return safe
