---
name: x2video-studio-ui
description: Design, implement, and visually verify X2Video Agent Studio screens. Use for React/Vite Studio pages, shared components, layout or interaction changes, and browser screenshot QA; do not use for the video-card HTML templates rendered into Publish Kits.
---

# X2Video Studio UI

Build a mature editorial control room, not a collection of generic dashboard cards. The interface exists to make the Agent's plan, evidence, decisions, failures, cost, and repairs observable and controllable.

## Before editing

1. Read `CONTEXT.md`, ADR-0010, and `docs/plans/agent-studio-v0.2-checklist.md`.
2. Inspect the API schemas and actual demo/live payloads. Never invent activity or duplicate business rules in React.
3. Read [references/visual-system.md](references/visual-system.md) before changing tokens, navigation, information hierarchy, or page composition.

## Product interaction rules

- Optimize desktop first for a 1440px editing workspace, then support 1024px and 390px without clipped primary actions.
- Keep persistent global context visible: Run state, autonomy, budget/cost, connection mode, and the active Gate.
- Prefer work surfaces, split panes, tables, timelines, inspectors, and inline diffs over repetitive rounded cards.
- Use progressive disclosure. Show decision summaries, confidence, risk, evidence, and repair actions; never expose hidden reasoning.
- Remove ornamental English kickers, redundant helper lines, repeated status prose, and metadata that does not change the next action. User-facing information must not depend on tiny 8–10px text.
- Every control must invoke a real API operation or be visibly disabled with an honest explanation.
- Design loading, empty, disconnected, error, waiting-human, canceled, and budget-stopped states as first-class states.
- Preserve keyboard focus, semantic labels, reduced-motion behavior, minimum 44px touch targets on narrow layouts, and WCAG AA contrast for essential text.
- Use neutral provider wording. Never display secrets, tokens, cookies, or raw authorization headers.

## Implementation rules

- Use shared design tokens and primitives, but compose distinctive page-level interfaces for Timeline, Curation Board, Script/Storyboard, and QC Lab.
- Keep server state in the API layer; use SSE to invalidate/refetch authoritative state. Do not simulate progress with timers.
- Keep URL-addressable pages and selected Run context so refresh/back/forward work.
- Make long Chinese text, URLs, IDs, missing media, large evidence sets, and dense traces wrap or scroll intentionally.
- Avoid decorative gradients, glow, glassmorphism, oversized hero copy, and excessive pill badges. Reserve color for state and hierarchy.
- Do not stop at a successful build. Browser verification is part of implementation.

## Required visual QA loop

1. Start the real API and Studio in Demo Mode.
2. Capture screenshots at 1440x1000 and 390x844 for each changed primary route.
3. Exercise at least one populated state and the most relevant adverse state (empty, error, waiting Gate, or repair needed).
4. Inspect screenshots for hierarchy, alignment, overflow, density, contrast, focus, sticky regions, and action discoverability.
5. Fix visible defects and repeat screenshots until no high/medium visual defects remain.
6. Run component tests, the production build, and UI E2E. Store the final screenshots under `artifacts/ui-qa/<date>/` and record commands and remaining low-risk defects in the phase report.

Never claim visual QA from DOM inspection alone. If the browser cannot run, report the blocker and do not mark the UI phase complete.
