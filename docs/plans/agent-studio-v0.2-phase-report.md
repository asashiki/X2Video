# Agent Studio v0.2 phase report

Each phase below records implementation, decisions, files/migrations, commands, proof, risks and the next entry point. Commit hashes are listed after the branch is finalized.

## Phase 0 — Baseline

- Completed: repository/Issue audit, OAuth test deadlock fix, Ruff baseline, ADR-0010, frozen implementation plan and validated project UI Skill.
- Decision: preserve the v0.1 CLI/output contract and add a bounded Kernel; no free multi-Agent framework and no UI-first mock.
- Main files: `docs/plans/agent-studio-v0.2-current-state.md`, `docs/adr/0010-bounded-agent-kernel-for-agent-studio.md`, `.codex/skills/x2video-studio-ui/`, OAuth tests.
- Migration: none.
- Commands: `pytest -q`, `ruff check .`, `x2video --help`, `x2video doctor`, Playwright install attempt.
- Result: the original hanging full suite became deterministic; FFmpeg/TTS were present, authentication optional, and the default Chromium CDN was unavailable in this container.
- Artifact: current-state audit and explicit external blockers.
- Screenshot: none; UI work had not started.
- Risk: issue #10's three-day unattended production proof and live credentials cannot be manufactured in an implementation session.
- Next: introduce versioned contracts and persistent state without changing legacy commands.

## Phase 1 — Kernel, Trace and persistence

- Completed: versioned Pydantic contracts, additive SQLite migrations/WAL, task state machine, budgets, retry, pause/resume/cancel, idempotency, redacted DB/JSONL Trace, Replay/fork and legacy Tool wrappers.
- Decision: SQLite is the Agent control plane; media remains on disk; compatibility file checks remain a v0.1 fallback.
- Main files: `x2video/domain/models.py`, `x2video/storage/`, `x2video/agent/`, `x2video/tools/base.py`, `registry.py`, `legacy_pipeline.py`.
- Migration: schema versions 1 and 2; v2 adds `runs.is_paused` to early databases.
- Commands: focused storage/runtime tests followed by full Pytest and Ruff.
- Result: durable restart state, safe budget stop, non-repeated succeeded tasks and secret-redacted Trace are test-covered.
- Artifact: `work/traces/<run_id>.jsonl` and SQLite Run snapshots.
- Screenshot: not applicable.
- Risk: SQLite is intentionally single-node; this release does not claim cloud multi-user coordination.
- Next: make research and decisions evidence-first.

## Phase 2 — Evidence and Curation

- Completed: frozen Candidate fixtures, EvidencePack/Claims/sources/confidence, Thread/Quote/Meme context, prompt-injection boundary, multi-dimensional Curation, de-duplication, shortage downgrade and explainable decisions.
- Decision: external text is always data; risk flags lower confidence and prevent selection before any script work.
- Main files: `tests/fixtures/demo/`, `tests/fixtures/evals/`, `x2video/security.py`, `x2video/tools/content.py`.
- Migration: Evidence and Decision tables are part of migration 1.
- Commands: Demo integration test and fixed Eval research/curation cases.
- Result: every selected Pick owns an EvidencePack; instruction-like rumor, Meme and duplicate cases are rejected.
- Artifact: `evidence.json`, `curation.json`, persisted Evidence/Decision rows.
- Screenshot: `artifacts/ui-qa/2026-08-29/*curation.png`.
- Risk: open-world entity/date verification remains Provider-specific; the fixed suite validates the deterministic boundary, not every future source.
- Next: ground Script facts and Storyboard scenes to Evidence IDs.

## Phase 3 — Script and Storyboard

- Completed: Grounded Script, Claim-Evidence map, typed Critic issue, single-Segment patch, lock enforcement, persisted diff and three format-specific Storyboard templates.
- Decision: Critic edits the smallest affected Segment and never exceeds two rounds.
- Main files: `x2video/tools/content.py`, domain Script/Storyboard contracts, application edit actions.
- Migration: Script issues use their own table.
- Commands: Demo integration and API action tests.
- Result: the intentional “逐步开放 → 全面开放” overclaim is detected and only Segment 02 reaches revision 2.
- Artifact: `script.draft.json`, `script.final.json`, `script.review.json`, `claim_map.json`, `storyboard.json`.
- Screenshot: `artifacts/ui-qa/2026-08-29/*script.png`.
- Risk: dependency-driven scene invalidation is still narrower than the long-term design; this release records the affected scene and bounded repair.
- Next: inspect real media and produce before/after repair proof.

## Phase 4 — QC and Repair

- Completed: real FFmpeg duration, black-frame, silence and volume inspection; safe-area QualityIssue; bounded Patch Handler; rerender and regression report; blocker protection.
- Decision: unresolved blockers fail the task; they are never converted to a publishable success by UI state.
- Main files: `x2video/tools/content.py`, `tests/test_quality_media_checks.py`, Demo integration tests.
- Migration: typed Quality Issues are persisted in migration 1.
- Commands: FFmpeg defect tests and full Demo run.
- Result: known black/silence/loud inputs are detected; Demo's 1810px subtitle boundary is repaired to 1620px in one round and regression passes.
- Artifact: Golden `video.mp4`, `cover.png`, `qc.before.json`, `repair.json`, `qc.after.json`.
- Screenshot: `artifacts/ui-qa/2026-08-29/*qc.png`.
- Risk: the deterministic Demo rerenders the compact motion-graphic video; production adapters can further optimize scene-only media splicing.
- Next: expose the same state and actions through API, Worker and Studio.

## Phase 5 — Agent Studio

- Completed: FastAPI, SSE, independent Worker, production React/Vite/TypeScript app, all eight routes, real controls, packaged static build and real-browser QA at desktop/mobile sizes.
- Decision: a custom, light-by-default editorial workspace replaces generic component-library cards; dark mode remains available. The hierarchy removes ornamental microcopy and stripe/underline selection patterns, while self-hosted CJK fonts make rendering deterministic.
- Main files: `x2video/api/`, `x2video/application.py`, `studio/`, `scripts/ui_qa.py`, `tests/test_api.py`.
- Migration: `is_paused` v2 column supports visible pause/resume control.
- Commands: `npm test -- --run`, `npm run build`, API tests and `scripts/ui_qa.py`.
- Result: Studio creates and observes complete Runs, executes Gate/curation/script/memory actions, plays real media and supports client-side routes from the packaged server.
- Artifact: production bundle under `x2video/api/static/`.
- Screenshot: 32 theme/route/viewport captures plus four contact sheets under `artifacts/ui-qa/2026-08-30/`.
- Risk: native browser prompts are used for the compact one-Segment replacement interaction; a richer diff editor is future UX refinement.
- Next: add approved Memory and fixed release evaluation.

## Phase 6 — Memory and Eval

- Completed: feedback, pending preference Memory, approval/rejection, provenance, controlled next-Goal context, fixed 30-case Eval, deterministic/semantic score fields and JSON/Markdown/HTML compare reports.
- Decision: unapproved feedback never becomes long-term context; Eval reports distinguish fixed feature coverage from open-world quality.
- Main files: `x2video/evals/`, `x2video/cli/eval.py`, API Memory routes, `evals/reports/`.
- Migration: Feedback, Memory, FTS, metrics and prompt-version tables are present in migration 1.
- Commands: `x2video eval run --profile baseline`, `x2video eval run --profile v0.2`, `x2video eval compare …`.
- Result: frozen v0.1 capability baseline 2/30; v0.2 fixed suite 30/30; +93.3 percentage points.
- Artifact: final report triplets and comparison in `evals/reports/`.
- Screenshot: Memory and Settings routes are included in UI QA.
- Risk: no benchmark source markdown exists beyond README, so transcription/distillation and performance CSV learning are deliberately not claimed.
- Next: stabilize Demo, package proof and finish operator docs.

## Phase 7 — Demo and delivery

- Completed: offline Demo, one-command Studio, CLI surface, 10-run stability script, Golden Demo Publish Kit, architecture/migration/troubleshooting docs and three-minute script.
- Decision: frozen model-equivalent responses make the competition path network-independent; live-source validation remains a separately labeled task.
- Main files: README, `scripts/demo_smoke.py`, `docs/architecture-agent-studio.md`, `docs/demo/`, `docs/migrations/`, `artifacts/`.
- Migration: rollback is non-destructive because v0.1 ignores Agent-only state.
- Commands: full Python/frontend gates, Doctor, UI QA, 10-run smoke, Eval compare and CLI help.
- Result: 10/10 Runs completed in 52.368 seconds; each produced 20 events, real media, one bounded repair and passing QC.
- Artifact: `artifacts/demo-stability.json` and `artifacts/golden-publish-kit/`.
- Screenshot: final contact sheet and individual desktop/mobile routes.
- Risk: official X MCP, three-day unattended live operation and real-sample Distillation remain honest follow-up items tied to existing Issues.
- Next: draft PR review; do not merge automatically.
