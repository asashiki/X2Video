# X2Video Agent Studio v0.2 implementation checklist

This is the reviewable implementation ledger. A checked item requires a test, Artifact, screenshot, or recorded command; code shape alone is not proof.

## Phase 0 — Baseline

- [x] Read repository instructions, glossary, ADRs, required pipeline files, tests, config/output conventions, open Issues, and supplied v0.2 documents.
- [x] Record current architecture, commands, output paths, Issue status, and observed baseline failures.
- [x] Add ADR-0010 for the bounded Agent Kernel.
- [x] Add and validate the project-local `x2video-studio-ui` Skill.
- [x] Fix the OAuth test hang and make full `pytest -q` terminate.
- [x] Establish a clean lint baseline.
- [ ] Add frozen Demo Candidate/Evidence fixtures.
- [ ] Save a reproducible Golden Publish Kit and baseline metrics.
- [ ] Record compatibility command/path tests.

## Phase 1 — Kernel, storage, trace

- [ ] Versioned domain models for Goal, Budget, Plan, Task, Event, Tool Call, Artifact, Evidence, Editorial, Script, Storyboard, Quality, Feedback, Memory, and Eval.
- [ ] SQLite migrations and tables for the required control-plane entities.
- [ ] Stable Run ID, task status transitions, optimistic/transactional updates, and recovery.
- [ ] Tool registry, idempotency keys, input hashes, Artifact dependencies, and legacy pipeline wrappers.
- [ ] Bounded retry, cancel, elapsed/call/cost budgets, and safe budget stop.
- [ ] Redacted JSONL trace and database payloads.
- [ ] Replay and checkpoint fork.
- [ ] Compatibility Plan preserves legacy CLI and outputs.

## Phase 2 — Evidence and Curation

- [ ] Evidence source/claim packs with freshness, trust signals, conflicts, and confidence.
- [ ] Thread/quote/reply/link context interfaces and frozen responses.
- [ ] Untrusted-content envelope, length limits, and injection risk flags.
- [ ] Deterministic checks for dates, numbers, versions, and proper nouns.
- [ ] Dimension scoring plus diverse Portfolio selection.
- [ ] Explainable Gate 1 with alternatives and risk blocking.

## Phase 3 — Grounded Script and Storyboard

- [ ] Outline and Claim Plan grounded to Evidence IDs.
- [ ] Versioned Script segments and Claim-Evidence map.
- [ ] Fact/style critic producing typed segment issues.
- [ ] At most two patch rounds; locked segments remain unchanged; diffs persist.
- [ ] `news_recap`, `single_explainer`, and `thread_story` Storyboards.
- [ ] Scene validation and dependency-based local invalidation.

## Phase 4 — QC and repair

- [ ] Structural, fact, subtitle, visual, and audio graders.
- [ ] FFmpeg black/silence/loudness checks and safe-area/subtitle checks.
- [ ] Typed Quality Issues with severity and repairability.
- [ ] Patch handlers and bounded two-round local repair.
- [ ] Regression QC and before/after evidence.
- [ ] Blockers cannot reach publishable/complete state.

## Phase 5 — Agent Studio

- [ ] FastAPI application service routes, worker isolation, SSE, and error contracts.
- [ ] Dashboard and Intent Composer.
- [ ] Agent Timeline with real controls, cost, Trace, Diff, Replay, and Gate reason.
- [ ] Curation Board with ordering, decision explanation, evidence, lock/research/replace actions.
- [ ] Script/Storyboard three-pane editor with segment patch and Claim mapping.
- [ ] QC Lab with player, issues, metrics, before/after, and scene repair.
- [ ] Memory/Benchmarks and Settings/Doctor.
- [ ] Apply the `x2video-studio-ui` Skill and its visual system.
- [ ] Component tests, production build, and real UI E2E.
- [ ] Screenshot QA at 1440x1000 and 390x844 for populated and adverse states; iterate until no high/medium visual defects remain.

## Phase 6 — Memory, Distillation, Eval

- [ ] Preference, production, and performance Memory with candidate approval, provenance, expiry, and rollback.
- [ ] Performance CSV import.
- [ ] Benchmark ingestion/transcription review contract.
- [ ] Prompt/Rubric versions, reviewable Distillation diff, eval gate, promotion, and rollback.
- [ ] Frozen 30–50 case Eval dataset covering content, provider, media, and recovery failures.
- [ ] Deterministic/semantic graders and JSON/Markdown/HTML comparison reports.

## Phase 7 — Demo and delivery

- [ ] `x2video studio`, `x2video agent run`, replay, feedback, and eval commands documented.
- [ ] Fully offline Demo Mode with fixed inputs, cached model responses, and media.
- [ ] Demo Mode passes ten consecutive runs.
- [ ] One real Publish Kit is separately verified without conflating it with Demo Mode.
- [ ] Three-minute demo script and architecture diagram.
- [ ] README, install, Doctor, troubleshooting, migration and rollback docs.
- [ ] `pytest -q`, `ruff check .`, CLI help/Doctor, UI tests/build/E2E, screenshots, and artifacts recorded.
- [ ] Small reviewable commits and a draft PR; do not merge automatically.
