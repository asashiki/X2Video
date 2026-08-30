# v0.2 verification report

Verification date: 2026-08-29. Environment: Python 3.12.13, Node 24.19.0, FFmpeg 6.1.1, portable Chromium 149.0.7827.0.

## Recorded proof

| Area | Command / artifact | Observed result |
|---|---|---|
| Python | `.venv/bin/pytest -q` | 55 passed in 22.12 s; one upstream Starlette/httpx deprecation warning |
| Lint | `.venv/bin/ruff check .` | pass |
| Frontend | `npm test -- --run` | 1 passed |
| Production UI | `npm run build` | pass; React bundle and two self-hosted Chinese WOFF2 fonts |
| Doctor | `X2VIDEO_BROWSER_EXECUTABLE=/tmp/chromium .venv/bin/x2video doctor` | required checks pass; optional Grok auth is absent |
| UI E2E | `.venv/bin/python scripts/ui_qa.py --chromium /tmp/chromium` | 32 screenshots across two themes, eight routes and two viewports |
| Demo stability | `.venv/bin/python scripts/demo_smoke.py --runs 10` | 10/10 complete in 52.368 s; every Run has 20 events, one repair and passing QC |
| Eval | `x2video eval run --profile v0.2` | 30/30 fixed cases pass |
| Baseline compare | `x2video eval compare …` | v0.1 capability baseline 6.7% → v0.2 100%, +93.3 points |

The Eval percentage is a deterministic feature-suite result, not a claim about open-world model quality. The v0.1 side is a frozen capability baseline because v0.1 has no Evidence, Agent Trace or repair schemas.

## Artifacts

- `artifacts/golden-publish-kit/` — real video, cover, Script Critic diff, Storyboard, Trace and QC before/after.
- `artifacts/demo-stability.json` — per-iteration IDs, timing, event count, media size and repair result.
- `artifacts/ui-qa/2026-08-30/` — light/dark populated route screenshots at desktop and mobile sizes.
- `evals/reports/` — versioned JSON, Markdown and HTML reports plus comparison.

## Honest external gaps

- No live X, model or TTS request was made for Demo/Eval proof.
- Official X MCP/REST remains issue #1 and is not represented as complete.
- Benchmark source files for issue #6 were not present, so real-sample transcription/distillation was not fabricated.
- The requested three-day unattended production run from issue #10 cannot be compressed into this implementation session; the existing scheduler path and the new 10-run deterministic stability proof are separately documented.
