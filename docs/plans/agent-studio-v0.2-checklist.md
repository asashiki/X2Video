# X2Video Agent Studio v0.2 implementation checklist

This is the reviewable implementation ledger. A checked item requires a test, Artifact, screenshot, or recorded command; code shape alone is not proof.

## Phase 0 — Baseline

- [x] Read repository instructions, glossary, ADRs, required pipeline files, tests, config/output conventions, open Issues, and supplied v0.2 documents.
- [x] Record current architecture, commands, output paths, Issue status, and observed baseline failures.
- [x] Add ADR-0010 for the bounded Agent Kernel.
- [x] Add and validate the project-local `x2video-studio-ui` Skill.
- [x] Fix the OAuth test hang and make full `pytest -q` terminate.
- [x] Establish a clean lint baseline.
- [x] Add frozen Demo Candidate/Evidence fixtures.
- [x] Save a reproducible Golden Publish Kit and baseline metrics.
- [x] Record compatibility command/path tests.

## Phase 1 — Kernel, storage, trace

- [x] Versioned domain models for Goal, Budget, Plan, Task, Event, Tool Call, Artifact, Evidence, Editorial, Script, Storyboard, Quality, Feedback, Memory, and Eval.
- [x] SQLite migrations and tables for the required control-plane entities.
- [x] Stable Run ID, task status transitions, transactional updates, pause/resume, and recovery.
- [x] Tool registry, idempotency keys, input hashes, Artifact dependencies, and legacy pipeline wrappers.
- [x] Bounded retry, cancel, elapsed/call/cost budgets, and safe budget stop.
- [x] Redacted JSONL trace and database payloads.
- [x] Replay and checkpoint fork.
- [x] Compatibility Plan wraps the ordered legacy CLI stages without changing their output paths.

## Phase 2 — Evidence and Curation

- [x] Evidence source/claim packs with freshness, trust signals, risk flags, and confidence.
- [x] Thread/quote context interfaces and frozen responses.
- [x] Untrusted-content envelope, length limits, and injection risk flags.
- [ ] Expand deterministic checks beyond the current supported/unsupported Claim comparison to a general date/number/version/proper-noun checker.
- [x] Dimension scoring plus de-duplicated Portfolio selection and explicit candidate-shortage downgrade.
- [x] Explainable Gate 1 with alternatives and risk blocking.

## Phase 3 — Grounded Script and Storyboard

- [x] Grounded Script composition plan from selected Evidence Claims.
- [x] Versioned Script segments and Claim-Evidence map.
- [x] Fact critic producing typed segment issues.
- [x] At most two patch rounds; locked segments remain unchanged; diffs persist.
- [x] `news_recap`, `single_explainer`, and `thread_story` Storyboards.
- [ ] Add dependency-based local invalidation beyond the current affected-scene repair declaration.

## Phase 4 — QC and repair

- [x] Structural, fact, subtitle, visual, and audio graders for the fixed suite.
- [x] FFmpeg black/silence/loudness checks and safe-area/subtitle checks.
- [x] Typed Quality Issues with severity and repairability.
- [x] Safe-area Patch Handler with a bounded two-round repair budget.
- [x] Regression QC and before/after evidence.
- [x] Unresolved blockers cannot reach publishable/complete state.

## Phase 5 — Agent Studio

- [x] FastAPI application service routes, worker isolation, SSE, and error contracts.
- [x] Dashboard and Intent Composer.
- [x] Agent Timeline with real controls, cost, Trace, Replay, Gate reason and fork.
- [x] Curation Board with ordering, decision explanation, evidence, research and replace actions.
- [x] Script/Storyboard three-pane editor with segment lock/patch and Claim mapping.
- [x] QC Lab with real player, issues, metrics, before/after and auto-repair evidence.
- [x] Memory/Benchmarks and Settings/Doctor.
- [x] Apply the `x2video-studio-ui` Skill and its visual system.
- [x] Component tests, production build, and real UI E2E.
- [x] Screenshot QA at 1440x1000 and 390x844 for eight populated routes; bundled CJK fonts and player cover were iterated from observed defects.

## Phase 6 — Memory, Distillation, Eval

- [x] Preference Memory with candidate approval, provenance, rejection and controlled use in the next Goal.
- [ ] Production/performance Memory and expiry automation.
- [ ] Performance CSV import.
- [ ] Benchmark ingestion/transcription review contract.
- [ ] Prompt/Rubric versions, reviewable Distillation diff, eval gate, promotion, and rollback.
- [x] Frozen 30-case Eval dataset covering content, provider, media, and recovery failures.
- [x] Deterministic plus bounded semantic score fields and JSON/Markdown/HTML comparison reports.

## Phase 7 — Demo and delivery

- [x] `x2video studio`, `x2video agent run`, replay, feedback, and eval commands documented.
- [x] Fully offline Demo Mode with fixed inputs, deterministic model-equivalent responses, and generated media.
- [x] Demo Mode passes ten consecutive runs.
- [ ] Verify one live-source, real-provider Publish Kit separately; the committed Golden Kit is explicitly Demo Mode.
- [x] Three-minute demo script and architecture diagram.
- [x] README, install, Doctor, troubleshooting, migration and rollback docs.
- [ ] `pytest -q`, `ruff check .`, CLI help/Doctor, UI tests/build/E2E, screenshots, and artifacts recorded.
- [x] Small reviewable commits; draft PR is the final handoff action and will not be merged automatically.
