"""Offline-capable v0.2 content tools used by Demo Mode and deterministic tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from x2video.domain.models import (
    Artifact,
    ClaimEvidence,
    ClaimEvidenceMap,
    EditorialDecision,
    EvidencePack,
    EvidenceSource,
    GroundedScript,
    GroundedSegment,
    QualityIssue,
    RepairAction,
    ScenePlan,
    ScriptIssue,
    Storyboard,
)
from x2video.security import envelope_untrusted
from x2video.storage.run_store import RunStore
from x2video.tools.base import AgentTool, ToolContext, ToolResult


def _root(context: ToolContext) -> Path:
    path = Path(context.work_dir) / "agent_runs" / context.run_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.model_dump(mode="json"),
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(run_id: str, kind: str, path: Path, *, depends_on: list[str] | None = None) -> Artifact:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return Artifact(
        run_id=run_id,
        kind=kind,
        path=str(path),
        mime_type="application/json" if path.suffix == ".json" else None,
        input_hash=digest,
        depends_on=depends_on or [],
    )


def _fixture_path(context: ToolContext) -> Path:
    supplied = context.payload.get("fixture_path")
    if supplied:
        return Path(str(supplied))
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "demo" / "candidates.json"


class DiscoverTool(AgentTool):
    name = "content.discover"

    async def execute(self, context: ToolContext) -> ToolResult:
        fixture = _fixture_path(context)
        payload = _read(fixture)
        destination = _write(_root(context) / "candidates.json", payload)
        artifact = _artifact(context.run_id, "candidates", destination)
        return ToolResult(
            summary=f"发现 {len(payload['candidates'])} 个 Candidate",
            artifacts=[artifact],
            payload={"candidate_count": len(payload["candidates"]), "mode": "demo"},
        )


class EvidenceResearchTool(AgentTool):
    name = "evidence.research"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        candidates = _read(_root(context) / "candidates.json")["candidates"]
        packs = []
        for candidate in candidates:
            context_parts = [
                str(candidate.get("thread_context") or ""),
                str(candidate.get("quoted_context") or ""),
            ]
            source_text = "\n".join([candidate["text"], *context_parts]).strip()
            _envelope, risks = envelope_untrusted(source_text)
            content_type = str(candidate.get("content_type") or "post")
            if content_type == "meme":
                risks.append("meme_or_satire")
            support = int(candidate.get("independent_support", 0))
            if support == 0:
                risks.append("single_unverified_source")
            source = EvidenceSource(
                run_id=context.run_id,
                source_id=f"source_{candidate['id']}",
                url=candidate["url"],
                source_type={"thread": "x_thread", "quote": "x_quote", "meme": "x_meme"}.get(
                    content_type, "x_post"
                ),
                title=f"@{candidate['author_username']} 的原始发布",
                author=candidate["author_name"],
                excerpt=source_text,
                trust_signals=(
                    ["verified_author"] if candidate.get("author_verified") else []
                ) + [f"independent_support:{support}"],
                risk_flags=sorted(set(risks)),
            )
            claims = [
                ClaimEvidence(
                    claim_id=f"claim_{candidate['id']}_{index}",
                    normalized_claim=claim,
                    supporting_source_ids=[source.source_id],
                    confidence=min(0.55 + support * 0.18 + (0.12 if candidate.get("author_verified") else 0), 0.98),
                )
                for index, claim in enumerate(candidate.get("fixture_claims", []), start=1)
            ]
            confidence = min((sum(c.confidence for c in claims) / max(len(claims), 1)), 0.98)
            if risks:
                confidence = min(confidence, 0.45)
            pack = EvidencePack(
                run_id=context.run_id,
                evidence_pack_id=f"evidence_{candidate['id']}",
                candidate_id=candidate["id"],
                sources=[source],
                claims=claims,
                freshness_score=0.94,
                context_completeness=min(0.45 + support * 0.22, 0.95),
                overall_confidence=round(confidence, 3),
                risk_flags=sorted(set(risks)),
            )
            self.store.add_evidence(pack)
            packs.append(pack)
        path = _write(_root(context) / "evidence.json", {"items": packs})
        artifact = _artifact(context.run_id, "evidence_pack", path)
        return ToolResult(
            summary=f"为 {len(packs)} 个 Candidate 建立 EvidencePack",
            artifacts=[artifact],
            payload={
                "pack_count": len(packs),
                "risk_count": sum(bool(pack.risk_flags) for pack in packs),
            },
        )


class PortfolioCuratorTool(AgentTool):
    name = "portfolio.curate"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        candidates = _read(_root(context) / "candidates.json")["candidates"]
        packs = {item["candidate_id"]: item for item in self.store.payloads("evidence", context.run_id)}
        decisions: list[EditorialDecision] = []
        eligible: list[tuple[float, dict[str, Any]]] = []
        for candidate in candidates:
            pack = packs[candidate["id"]]
            duplicate = bool(candidate.get("duplicate_of"))
            risk = bool(pack["risk_flags"])
            engagement = min(candidate.get("likes", 0) / 15_000, 1.0)
            trust = pack["overall_confidence"]
            visual = 0.9 if candidate.get("media_urls") else 0.55
            score = round(0.30 * trust + 0.25 * engagement + 0.20 * 0.9 + 0.15 * visual + 0.10 * 0.85, 3)
            if not risk and not duplicate:
                eligible.append((score, candidate))
            rejected = []
            if risk:
                rejected.append("证据不足或含 Prompt Injection 风险")
            if duplicate:
                rejected.append(f"与 {candidate['duplicate_of']} 是同一新闻")
            decisions.append(
                EditorialDecision(
                    run_id=context.run_id,
                    decision_id=f"decision_{candidate['id']}",
                    candidate_id=candidate["id"],
                    selected=False,
                    dimension_scores={
                        "goal_relevance": 0.9,
                        "audience_value": 0.85,
                        "freshness": 0.94,
                        "source_trust": trust,
                        "visual_material": visual,
                        "novelty": 0.1 if duplicate else 0.88,
                    },
                    confidence=trust,
                    decision_summary="进入组合候选" if not rejected else rejected[0],
                    evidence_ids=[pack["evidence_pack_id"]],
                    risk_flags=pack["risk_flags"],
                    rejected_because=rejected,
                )
            )
        selected_ids = [candidate["id"] for _score, candidate in sorted(eligible, reverse=True)[:3]]
        rank = 0
        for decision in decisions:
            if decision.candidate_id in selected_ids:
                rank += 1
                decision.selected = True
                decision.rank = rank
                decision.decision_summary = "可信、时效和中文受众价值较高，进入 Digest"
            else:
                decision.alternatives = selected_ids[:1]
            self.store.add_decision(decision)
        shortage = len(selected_ids) < 3
        path = _write(
            _root(context) / "curation.json",
            {
                "selected_ids": selected_ids,
                "decisions": decisions,
                "candidate_shortage": shortage,
            },
        )
        artifact = _artifact(context.run_id, "editorial_decisions", path)
        return ToolResult(
            summary=(
                f"组合选择 {len(selected_ids)} 个 Pick，淘汰 {len(decisions) - len(selected_ids)} 个"
                + ("；可信 Candidate 不足，明确降级为短 Digest" if shortage else "")
            ),
            artifacts=[artifact],
            payload={
                "selected_ids": selected_ids,
                "rejected": len(decisions) - len(selected_ids),
                "candidate_shortage": shortage,
            },
        )


class ScriptComposeTool(AgentTool):
    name = "script.compose"

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        selected = _read(root / "curation.json")["selected_ids"]
        candidates = {item["id"]: item for item in _read(root / "candidates.json")["candidates"]}
        packs = {item["candidate_id"]: item for item in _read(root / "evidence.json")["items"]}
        segments = []
        for candidate_id in selected:
            candidate = candidates[candidate_id]
            claims = packs[candidate_id]["claims"]
            narration = "；".join(claim["normalized_claim"] for claim in claims) + "。"
            if candidate.get("inject_script_overclaim"):
                narration = narration.replace("逐步开放", "全面开放")
            segments.append(
                GroundedSegment(
                    pick_id=candidate_id,
                    narration=narration,
                    evidence_ids=[packs[candidate_id]["evidence_pack_id"]],
                )
            )
        script = GroundedScript(
            run_id=context.run_id,
            hook="今天 AI 圈有三件事值得看，但其中一条差点被写过头。",
            segments=segments,
            outro="以上信息都保留了来源与不确定性，完整证据可以在 Studio 查看。",
            title_suggestions=["今天 AI 圈最值得看的三件事", "一条新闻差点被写过头"],
            description="基于冻结公开数据制作的 X2Video Agent Studio Demo。",
            tags=["AI", "科技", "X2Video"],
        )
        path = _write(root / "script.draft.json", script)
        claim_maps = [
            ClaimEvidenceMap(
                run_id=context.run_id,
                segment_id=segment.segment_id,
                claim_ids=[claim["claim_id"] for claim in packs[segment.pick_id]["claims"]],
                evidence_ids=segment.evidence_ids,
                coverage=1.0 if segment.evidence_ids else 0.0,
            )
            for segment in script.segments
        ]
        claim_map_path = _write(root / "claim_map.json", {"items": claim_maps})
        artifacts = [
            _artifact(context.run_id, "script_draft", path),
            _artifact(context.run_id, "claim_evidence_map", claim_map_path),
        ]
        return ToolResult(
            summary=f"生成 {len(segments)} 段有 Evidence 引用的 Script 初稿",
            artifacts=artifacts,
            payload={"segment_count": len(segments), "injected_issue": True},
            llm_calls=1,
            cost_usd=0.012,
        )


class ScriptReviewTool(AgentTool):
    name = "script.review"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        script = GroundedScript.model_validate(_read(root / "script.draft.json"))
        diffs = []
        issues = []
        for segment in script.segments:
            if "全面开放" not in segment.narration:
                continue
            issue = ScriptIssue(
                run_id=context.run_id,
                segment_id=segment.segment_id,
                category="unsupported_claim",
                severity="error",
                message="Evidence 只支持“逐步向部分账号开放”，不支持“全面开放”。",
                patch_instruction="仅把“全面开放”改回“逐步开放”。",
                evidence_ids=segment.evidence_ids,
            )
            self.store.add_script_issue(issue)
            issues.append(issue)
            if not segment.locked:
                before = segment.narration
                segment.narration = segment.narration.replace("全面开放", "逐步开放")
                segment.revision += 1
                issue.resolved = True
                self.store.add_script_issue(issue)
                diffs.append({"segment_id": segment.segment_id, "before": before, "after": segment.narration})
        script_path = _write(root / "script.final.json", script)
        review_path = _write(root / "script.review.json", {"issues": issues, "diffs": diffs, "rounds": 1})
        artifacts = [
            _artifact(context.run_id, "script_final", script_path),
            _artifact(context.run_id, "script_review", review_path),
        ]
        return ToolResult(
            summary=f"Critic 检出 {len(issues)} 个问题并仅修订对应 Segment",
            artifacts=artifacts,
            payload={"issue_count": len(issues), "patched_segments": len(diffs), "rounds": 1},
            llm_calls=1,
            cost_usd=0.006,
        )


class StoryboardTool(AgentTool):
    name = "visual.storyboard"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        script = GroundedScript.model_validate(_read(root / "script.final.json"))
        snapshot = self.store.snapshot(context.run_id) or {}
        format_name = str((snapshot.get("plan") or {}).get("format", "news_recap"))
        scene_template = {
            "news_recap": "tweet_card",
            "single_explainer": "explainer_card",
            "thread_story": "thread_card",
        }.get(format_name, "tweet_card")
        scenes = [
            ScenePlan(
                pick_id=segment.pick_id,
                narration_ref=segment.segment_id,
                visual_source_ids=segment.evidence_ids,
                template=scene_template,
                duration_seconds=6.0,
                overlay_text=[segment.narration[:18]],
                attribution=f"source:{segment.pick_id}",
            )
            for segment in script.segments
        ]
        storyboard = Storyboard(
            run_id=context.run_id,
            template=format_name,
            scenes=scenes,
            expected_duration_seconds=sum(scene.duration_seconds for scene in scenes),
        )
        path = _write(root / "storyboard.json", storyboard)
        artifact = _artifact(context.run_id, "storyboard", path)
        return ToolResult(
            summary=f"规划 {len(scenes)} 个 Scene，均绑定 Script 与 Evidence",
            artifacts=[artifact],
            payload={"scene_count": len(scenes), "duration": storyboard.expected_duration_seconds},
        )


class ProducerTool(AgentTool):
    name = "producer.render"

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        publish = root / "publish_kit"
        publish.mkdir(parents=True, exist_ok=True)
        video = publish / "video.mp4"
        cover = publish / "cover.png"
        _render_demo_media(video, cover, repaired=False)
        manifest = {
            "schema_version": "1.0",
            "run_id": context.run_id,
            "video": str(video),
            "cover": str(cover),
            "subtitle_bottom": 1810,
            "safe_area_bottom": 1680,
            "repair_revision": 0,
        }
        manifest_path = _write(publish / "render_manifest.json", manifest)
        publish_md = publish / "publish.md"
        publish_md.write_text(
            "# Publish Kit\n\n- 视频: `video.mp4`\n- 封面: `cover.png`\n- Demo Mode: 冻结数据，不依赖实时 X 或模型。\n",
            encoding="utf-8",
        )
        artifacts = [
            _artifact(context.run_id, "video", video),
            _artifact(context.run_id, "cover", cover),
            _artifact(context.run_id, "render_manifest", manifest_path),
            _artifact(context.run_id, "publish_copy", publish_md),
        ]
        return ToolResult(
            summary="生成真实 MP4、PNG 与 Publish Kit，并注入一个可修复安全区问题",
            artifacts=artifacts,
            payload={"video": str(video), "cover": str(cover), "injected_qc_issue": True},
        )


class QualityReviewTool(AgentTool):
    name = "quality.review"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        manifest = _read(root / "publish_kit" / "render_manifest.json")
        video_path = Path(manifest["video"])
        duration = _probe_duration(video_path)
        media_checks = _probe_media_checks(video_path)
        issues = []
        if manifest["subtitle_bottom"] > manifest["safe_area_bottom"]:
            issue = QualityIssue(
                run_id=context.run_id,
                issue_id=f"quality_{context.run_id}_safe_area",
                code="SUBTITLE_SAFE_AREA",
                category="subtitle",
                severity="error",
                timestamp_seconds=3.2,
                evidence=[f"subtitle_bottom={manifest['subtitle_bottom']}", f"safe_max={manifest['safe_area_bottom']}"],
                description="字幕底边越过竖屏平台安全区。",
                auto_fixable=True,
                proposed_patch={"subtitle_bottom": 1620, "rerender": "affected_scene"},
            )
            self.store.add_quality_issue(issue)
            issues.append(issue)
        if media_checks["black_segments"]:
            issue = QualityIssue(
                run_id=context.run_id,
                issue_id=f"quality_{context.run_id}_black_frame",
                code="BLACK_FRAME",
                category="visual",
                severity="blocker",
                evidence=media_checks["black_segments"],
                description="FFmpeg blackdetect found a sustained black frame.",
            )
            self.store.add_quality_issue(issue)
            issues.append(issue)
        if media_checks["silence_segments"]:
            issue = QualityIssue(
                run_id=context.run_id,
                issue_id=f"quality_{context.run_id}_silence",
                code="UNEXPECTED_SILENCE",
                category="audio",
                severity="blocker",
                evidence=media_checks["silence_segments"],
                description="FFmpeg silencedetect found sustained silence.",
            )
            self.store.add_quality_issue(issue)
            issues.append(issue)
        if media_checks["mean_volume_db"] is not None and media_checks["mean_volume_db"] > -12:
            issue = QualityIssue(
                run_id=context.run_id,
                issue_id=f"quality_{context.run_id}_loudness",
                code="AUDIO_TOO_LOUD",
                category="audio",
                severity="error",
                evidence=[f"mean_volume={media_checks['mean_volume_db']}dB"],
                description="FFmpeg volumedetect reports an overly loud mix.",
            )
            self.store.add_quality_issue(issue)
            issues.append(issue)
        report = {
            "schema_version": "1.0",
            "duration_seconds": duration,
            "checks": {
                "video_exists": True,
                "cover_exists": True,
                "safe_area": not any(item.code == "SUBTITLE_SAFE_AREA" for item in issues),
                "black_frames": not media_checks["black_segments"],
                "silence": not media_checks["silence_segments"],
                "loudness": not any(item.code == "AUDIO_TOO_LOUD" for item in issues),
            },
            "ffmpeg_diagnostics": media_checks,
            "issues": [issue.model_dump(mode="json") for issue in issues],
        }
        path = _write(root / "publish_kit" / "qc.before.json", report)
        artifact = _artifact(context.run_id, "quality_report_before", path)
        return ToolResult(
            summary=f"QC 完成：检出 {len(issues)} 个可定位问题",
            artifacts=[artifact],
            payload={
                "issue_count": len(issues),
                "blockers": sum(item.severity == "blocker" for item in issues),
                "auto_fixable": sum(item.auto_fixable for item in issues),
            },
        )


class RepairTool(AgentTool):
    name = "quality.repair"

    def __init__(self, store: RunStore) -> None:
        self.store = store

    async def execute(self, context: ToolContext) -> ToolResult:
        root = _root(context)
        manifest_path = root / "publish_kit" / "render_manifest.json"
        manifest = _read(manifest_path)
        unresolved = [
            QualityIssue.model_validate(item)
            for item in self.store.payloads("quality_issues", context.run_id)
            if not item.get("resolved") and item.get("auto_fixable")
        ]
        actions = []
        for issue in unresolved[:2]:
            manifest.update(issue.proposed_patch or {})
            manifest["repair_revision"] = int(manifest.get("repair_revision", 0)) + 1
            _render_demo_media(Path(manifest["video"]), Path(manifest["cover"]), repaired=True)
            self.store.resolve_quality_issue(issue)
            actions.append(
                RepairAction(
                    run_id=context.run_id,
                    issue_id=issue.issue_id,
                    handler="subtitle_safe_area_patch",
                    summary="将字幕底边移回安全区并只重渲染受影响场景。",
                    attempt=1,
                    succeeded=True,
                )
            )
        _write(manifest_path, manifest)
        unresolved_after = [
            item
            for item in self.store.payloads("quality_issues", context.run_id)
            if not item.get("resolved")
        ]
        regression = {
            "schema_version": "1.0",
            "ok": manifest["subtitle_bottom"] <= manifest["safe_area_bottom"] and not unresolved_after,
            "checks": {"safe_area": True, "video_rebuilt": bool(actions)},
            "actions": [action.model_dump(mode="json") for action in actions],
            "unresolved": unresolved_after,
        }
        repair_path = _write(root / "publish_kit" / "repair.json", {"actions": actions})
        qc_path = _write(root / "publish_kit" / "qc.after.json", regression)
        if unresolved_after:
            codes = ", ".join(str(item.get("code")) for item in unresolved_after)
            raise RuntimeError(f"QC blockers remain unresolved: {codes}")
        artifacts = [
            _artifact(context.run_id, "repair_report", repair_path),
            _artifact(context.run_id, "quality_report_after", qc_path),
            _artifact(context.run_id, "render_manifest_repaired", manifest_path),
        ]
        return ToolResult(
            summary=f"自动修复 {len(actions)} 个问题并通过回归 QC",
            artifacts=artifacts,
            payload={"repaired": len(actions), "regression_ok": regression["ok"], "rounds": 1},
        )


def register_content_tools(registry: Any, store: RunStore) -> None:
    for tool in (
        DiscoverTool(),
        EvidenceResearchTool(store),
        PortfolioCuratorTool(store),
        ScriptComposeTool(),
        ScriptReviewTool(store),
        StoryboardTool(store),
        ProducerTool(),
        QualityReviewTool(store),
        RepairTool(store),
    ):
        registry.register(tool)


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return round(float(result.stdout.strip()), 3)


def _probe_media_checks(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.35:pix_th=0.02",
            "-af",
            "silencedetect=n=-50dB:d=0.5,volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stderr
    black_segments = [line.strip() for line in output.splitlines() if "black_start:" in line]
    silence_segments = [line.strip() for line in output.splitlines() if "silence_start:" in line]
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", output)
    return {
        "black_segments": black_segments,
        "silence_segments": silence_segments,
        "mean_volume_db": float(match.group(1)) if match else None,
    }


def _ffmpeg_fontfile(path: Path) -> str:
    """Escape a local TTF path for FFmpeg drawtext (Windows drive letters included)."""
    posix = path.resolve().as_posix().replace(":", r"\:")
    return f"'{posix}'"


def _demo_font_candidates() -> list[tuple[Path, Path]]:
    windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    return [
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
        ),
        (windows_fonts / "arial.ttf", windows_fonts / "arialbd.ttf"),
        (windows_fonts / "segoeui.ttf", windows_fonts / "segoeuib.ttf"),
        (
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ),
        (Path("/Library/Fonts/Arial.ttf"), Path("/Library/Fonts/Arial Bold.ttf")),
    ]


def _demo_fonts() -> tuple[str, str]:
    configured_regular = os.environ.get("X2VIDEO_DEMO_FONT")
    configured_bold = os.environ.get("X2VIDEO_DEMO_FONT_BOLD")
    pairs: list[tuple[Path, Path]] = []
    if configured_regular:
        regular = Path(configured_regular)
        bold = Path(configured_bold) if configured_bold else regular
        pairs.append((regular, bold))
    pairs.extend(_demo_font_candidates())
    for regular, bold in pairs:
        if regular.exists() and bold.exists():
            return _ffmpeg_fontfile(regular), _ffmpeg_fontfile(bold)
    raise RuntimeError(
        "Demo Mode needs a TrueType font. Install DejaVu Sans, or set "
        "X2VIDEO_DEMO_FONT to an existing .ttf path."
    )


def _render_demo_media(video: Path, cover: Path, *, repaired: bool) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for Demo Mode production")
    color = "0x0b1726" if repaired else "0x121a2a"
    regular_font, bold_font = _demo_fonts()
    subtitle_y = 1620 if repaired else 1775
    common = [
        "drawbox=x=0:y=0:w=1080:h=16:color=0xf1ae52:t=fill",
        "drawtext="
        f"fontfile={bold_font}:text='X2VIDEO  //  AGENT STUDIO':"
        "x=76:y=76:fontsize=32:fontcolor=0xf1ae52",
        "drawtext="
        f"fontfile={regular_font}:text='EVIDENCE-LED AI BRIEFING':"
        "x=76:y=128:fontsize=22:fontcolor=0x8fa0b7",
        "drawbox=x=76:y=220:w=928:h=2:color=0x344154:t=fill",
        "drawtext="
        f"fontfile={regular_font}:text='29 AUG 2026  /  3 VERIFIED SIGNALS':"
        "x=76:y=256:fontsize=24:fontcolor=white@0.78",
    ]
    scenes = [
        (0, 2.66, "01", "COMPACT MODEL RELEASE", "Weights and evaluation notes are available."),
        (2.66, 5.33, "02", "GRADUAL FEATURE ROLLOUT", "Availability is expanding to selected accounts."),
        (5.33, 8.1, "03", "BENCHMARK UPDATE", "New multilingual agent results were published."),
    ]
    scene_filters = []
    for start, end, number, title, subtitle in scenes:
        enabled = f"enable='between(t,{start},{end})'"
        scene_filters.extend(
            [
                f"drawbox=x=76:y=390:w=928:h=720:color=0x111f31:t=fill:{enabled}",
                f"drawbox=x=76:y=390:w=10:h=720:color=0xf1ae52:t=fill:{enabled}",
                "drawtext="
                f"fontfile={bold_font}:text='SIGNAL {number}':x=124:y=455:"
                f"fontsize=28:fontcolor=0xf1ae52:{enabled}",
                "drawtext="
                f"fontfile={bold_font}:text='{title}':x=124:y=570:"
                f"fontsize=50:fontcolor=white:{enabled}",
                "drawtext="
                f"fontfile={regular_font}:text='{subtitle}':x=124:y=680:"
                f"fontsize=27:fontcolor=0xb8c4d4:{enabled}",
                f"drawbox=x=124:y=820:w=650:h=8:color=0x59c3d7:t=fill:{enabled}",
                "drawtext="
                f"fontfile={regular_font}:text='SOURCE VERIFIED   //   CONFIDENCE HIGH':"
                f"x=124:y=875:fontsize=21:fontcolor=0x61c68b:{enabled}",
                f"drawbox=x=76:y={subtitle_y}:w=928:h=92:color=black@0.78:t=fill:{enabled}",
                "drawtext="
                f"fontfile={regular_font}:text='{subtitle}':x=(w-text_w)/2:y={subtitle_y + 29}:"
                f"fontsize=25:fontcolor=white:{enabled}",
            ]
        )
    video_filter = ",".join(
        common
        + scene_filters
        + [
            "drawtext="
            f"fontfile={regular_font}:text='GROUNDING ON  /  REPAIR PASS 1 OF 2':"
            "x=76:y=1860:fontsize=18:fontcolor=0x687587"
        ]
    )
    video.parent.mkdir(parents=True, exist_ok=True)
    video_result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=1080x1920:r=30:d=8",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=48000:duration=8",
            "-t",
            "8",
            "-vf",
            video_filter,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-af",
            "volume=0.035",
            "-shortest",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if video_result.returncode:
        raise RuntimeError(f"Demo video render failed: {video_result.stderr[-1000:]}")
    cover_filter = ",".join(
        [
            "drawbox=x=0:y=0:w=1080:h=18:color=0xf1ae52:t=fill",
            "drawbox=x=80:y=128:w=88:h=88:color=0xf1ae52:t=fill",
            "drawtext="
            f"fontfile={bold_font}:text='X2':x=101:y=149:fontsize=44:fontcolor=0x15100a",
            "drawtext="
            f"fontfile={bold_font}:text='X2VIDEO':x=194:y=132:fontsize=44:fontcolor=white",
            "drawtext="
            f"fontfile={regular_font}:text='AGENT STUDIO':x=196:y=184:fontsize=20:"
            "fontcolor=0x8fa0b7",
            "drawtext="
            f"fontfile={bold_font}:text='AI SIGNALS':x=80:y=430:fontsize=104:fontcolor=white",
            "drawtext="
            f"fontfile={bold_font}:text='BRIEFING':x=80:y=548:fontsize=104:fontcolor=0xf1ae52",
            "drawbox=x=80:y=720:w=920:h=2:color=0x344154:t=fill",
            "drawtext="
            f"fontfile={regular_font}:text='03 VERIFIED STORIES':x=80:y=780:fontsize=30:"
            "fontcolor=0x61c68b",
            "drawtext="
            f"fontfile={regular_font}:text='Evidence mapped  /  Claims reviewed  /  QC repaired':"
            "x=80:y=850:fontsize=24:fontcolor=0xb8c4d4",
            "drawtext="
            f"fontfile={regular_font}:text='29 AUG 2026':x=80:y=1280:fontsize=24:"
            "fontcolor=0x687587",
        ]
    )
    cover_result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=1080x1440",
            "-frames:v",
            "1",
            "-vf",
            cover_filter,
            "-threads",
            "1",
            str(cover),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if cover_result.returncode:
        raise RuntimeError(f"Demo cover render failed: {cover_result.stderr[-1000:]}")
