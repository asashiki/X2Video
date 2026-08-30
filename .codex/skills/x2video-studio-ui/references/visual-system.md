# X2Video Agent Studio visual system

Use this reference when establishing or changing the shell, tokens, or primary page composition.

## Character

The product is an editorial operations desk: calm, exact, clear, and credible. It should feel closer to a professional desktop tool than a marketing dashboard. Default to a high-clarity light theme and provide an equally complete dark theme. Color communicates status; decoration does not compete with evidence.

Prefer immediate comprehension over visible sophistication. Do not add an eyebrow, subtitle, helper sentence, badge, ID, or metadata row unless it changes the user's next decision. Avoid the common generated-dashboard habit of explaining every control with a second line of small text. Essential detail remains available in the relevant inspector or expanded state.

## Tokens

- Canvas: soft neutral gray in the default light theme; near-black blue-neutral in dark mode, never pure white or pure black.
- Surface levels: clearly separated neutral levels using lightness and 1px borders, not blur.
- Text: high-contrast primary, muted metadata, subdued tertiary; avoid low-contrast gray-on-gray.
- Accent: warm amber for primary action focus. Selection uses a complete quiet surface and border, never a lone stripe on one edge or an underline.
- Status: green success, amber waiting/warning, red error/blocker, blue running/info, gray pending/canceled.
- Radius: 6–10px for controls and panels. Avoid fully rounded containers except compact status chips.
- Spacing: 4px base grid; dense controls use 8/12px, panels 16/20px, route gutters 24px.
- Typography: local UI stack such as `Inter Variable`, `IBM Plex Sans`, `Noto Sans SC`, system sans; monospaced stack for IDs, cost, timing, and trace payloads.

## Shell

- Left rail: product/route navigation with icons and text; collapsible at medium widths. The active route is a complete, quiet filled item—no left color bar, bottom bar, or decorative marker.
- Top bar: current Run context, theme switch and primary action. Add global search only when it is functional and materially useful; never reserve space for a decorative command box.
- Main: route-specific work surface; avoid a generic title plus card grid on every page.
- Inspector: contextual right pane for evidence, issue details, or Artifact metadata; collapsible and resizable where useful.

## Core route composition

### Dashboard

Lead with active Runs and actionable Gates. Metrics are compact and secondary. Recent outputs and Eval trend must link to authoritative detail.

### Intent Composer

Use a focused composition workspace: natural-language goal on the left, structured constraints and budget on the right, generated editable plan below. The execute action stays visible.

### Agent Timeline

Use a vertical event spine with compact task rows, duration/cost columns, expand-in-place details, and a persistent Run control strip. Waiting Gates and failed/repair loops must interrupt the rhythm visibly.

### Curation Board

Use a rankable editorial queue and evidence inspector. Candidate selection, rejection, lock, research request, and replacement must remain understandable without opening modal stacks.

### Script and Storyboard

Use a three-pane editor: evidence, script segments, scene plan. Locked segments and Claim-to-Evidence mappings need persistent visual cues; diffs should be line/segment scoped.

### QC Lab

Place the video and issue timeline together. Keep issue list, before/after evidence, audio/subtitle metrics, and scene repair action within one review path.

## Screenshot review checklist

- First glance reveals the current Run, state, next required action, and evidence/quality risk.
- Primary action is unambiguous; destructive actions are separated and confirmed.
- Dense data aligns to a clear grid; no orphan labels or floating metadata.
- Text does not truncate critical claims, issue descriptions, or Gate explanations.
- At 390px, navigation becomes a drawer or bottom surface, inspectors become sheets, tables become purposeful stacked rows, and controls remain reachable.
- Focus rings are visible; motion respects `prefers-reduced-motion`.
- Screenshots contain no credentials or private raw payloads.
