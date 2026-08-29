# X2Video Agent Studio v0.2 current-state audit

Audit date: 2026-08-29  
Audited commit: `0b336ef` (`main`)  
Upgrade branch: `feat/agent-studio-v0.2`

## Executive summary

X2Video v0.1 is a working Python CLI skeleton with real Candidate source abstraction, Curation and Script model calls, Playwright Tweet Card rendering, Edge/API-compatible TTS, FFmpeg composition, a Publish Kit, Gate 1 selection, Ledger de-duplication, and file-based resume. It is not yet an Agent runtime: there is no explicit goal or plan, durable task state, evidence graph, bounded critic/repair loop, replay, eval harness, or Studio API/UI.

The upgrade must wrap the existing pipeline as deterministic Tools. The current output layout and commands remain the compatibility contract while the new SQLite control plane becomes authoritative for Agent runs.

## Required reading completed

- `README.md`, `CONTEXT.md`, `AGENTS.md`, and `pyproject.toml`
- `x2video/pipeline/orchestrate.py`, `curate.py`, `script.py`, `render.py`, and `qc.py`
- ADR-0001 through ADR-0009
- all files under `tests/`
- `x2video.example.toml`, `.env.example`, config loader/schema, CLI entrypoints, Artifact I/O, work-directory and Ledger conventions
- all open GitHub Issues and their comments: #1, #6, and #10
- supplied v0.2 master prompt and upgrade plan

## Existing architecture

| Area | Current implementation | Compatibility requirement |
| --- | --- | --- |
| Orchestration | Fixed `fetch → curate → card → script → render` function | Preserve legacy commands and make this a Compatibility Plan |
| Resume | Stage output existence in `work/YYYY-MM-DD/` | Keep as fallback; Agent runs use durable task state and Artifact hashes |
| Source | Replaceable `CandidateSource`; SuperGrok X Search works; official X source is a placeholder | Keep adapter boundary; offline tests cannot depend on live X |
| Curation | One structured model call, threshold, top-N/indices, Gate 1 | Wrap as Tool, then add Evidence and Portfolio decisions |
| Script | One structured model call producing Digest segments | Preserve Digest N model; add Claim map, critic, locks and segment patching |
| Visual | HTML/CSS Tweet Cards and opener/cover rendered through Playwright | Reuse per ADR-0002/0009 |
| Production | Edge/API-compatible TTS and FFmpeg clips/concat/BGM | Reuse per ADR-0005/0007/0009 |
| QC | File size, ffprobe duration, cover existence, Pick-count warning | Preserve and extend to versioned `QualityIssue` plus bounded repair |
| Storage | JSON/Markdown/media files and `work/ledger.json` | Media stays in the filesystem; SQLite becomes the control plane |
| Publication | Publish Kit only; human upload | Preserve final Gate; no automatic platform publication |

## Current Artifact and output conventions

```text
work/
  ledger.json
  YYYY-MM-DD/
    candidates.json
    candidates.md
    scored.json
    picks.json
    cards/*.png
    script.json
    script.md
    audio/*.mp3
    clips/*.{ass,mp4}
    publish_kit.json

final/
  YYYY-MM-DD-HHMMSS/
    video.mp4
    cover.png
    publish.md
    qc.json
```

The v0.2 Artifact store may add metadata and new outputs but must not silently move or rename these legacy products.

## GitHub Issue status

- #10: `x2video run --auto`, file-based `--from-stage`, and scheduler documentation exist. The required real unattended three-day run has not been performed.
- #6: only Benchmark directory conventions and hand-written prompts exist. Transcription, Distillation, prompt versioning, reviewable diff, and eval promotion are missing.
- #1: a real token and REST field coverage were previously validated by the owner, but the official X MCP/REST adapter is still not implemented. The default usable path is the SuperGrok adapter. This is not a competition P0.

## Baseline commands and observed results

Environment: Python 3.12.13, Node 24.19.0, FFmpeg 6.1.1.

| Command | Result | Notes |
| --- | --- | --- |
| `.venv/bin/x2video --help` | Pass | Legacy command surface is present |
| `.venv/bin/pytest -q` | Blocked | Hangs after seven tests in `test_login_pkce_flow_end_to_end`; it performs a blocking callback request before the server handles it |
| `.venv/bin/pytest -q -k 'not login_pkce_flow_end_to_end'` | Pass | 36 passed, 1 deselected in 0.13s |
| `.venv/bin/ruff check .` | Fail | 59 pre-existing findings, including imports, broad exceptions, Typer B008, timezone and subprocess checks |
| `.venv/bin/x2video doctor` | Fail | FFmpeg and TTS imports pass; local auth is absent and Playwright Chromium is missing |
| `.venv/bin/playwright install chromium` | Blocked | CDN download timed out repeatedly in this environment |

No live X/LLM/TTS paid call was made during the audit. No credential was copied into the repository. A Golden Publish Kit and screenshot baseline are not yet claimed; they require the frozen Demo fixture and a working browser install.

## Principal gaps and risks

1. The new runtime needs a transactional state model without breaking the file-based CLI.
2. Existing model responses use loose dictionaries/JSON Schema rather than versioned Pydantic contracts.
3. Candidate text is inserted into prompts without an explicit untrusted-data envelope or injection scanner.
4. Current Curation is ranking, not portfolio composition, and Script facts are not traceable to Evidence.
5. QC cannot express typed issues, dependencies, repair actions, or regression state.
6. No application service exists for shared CLI/API/UI behavior.
7. No frozen Demo Mode means evaluations and demos depend on external services.
8. The current test suite has a deterministic hang and lint has no clean baseline.
9. The browser dependency must be made diagnosable and configurable before UI/card screenshot proof.

## Phase 0 exit criteria

- Fix the hanging OAuth test without weakening the production flow.
- Establish a frozen Candidate/Evidence fixture and deterministic compatibility run.
- Produce a Golden Publish Kit or explicitly record the remaining browser/TTS blocker.
- Add compatibility tests for legacy commands and paths.
- Bring `ruff check .` to green or define a narrow, documented configuration baseline before new code expands.
- Commit this audit, ADR-0010, the implementation checklist, and the validated Studio UI Skill.

