# X2Video

Agent instructions for this repository. Both Codex and Claude Code read this file
(`CLAUDE.md` routes here).

## Agent skills

### Issue tracker

Issues and PRDs are tracked in **GitHub Issues** on `asashiki/X2Video`, managed via the `gh` CLI. External pull requests are **not** treated as a triage surface. See `docs/agents/issue-tracker.md`.

### Triage labels

Uses the default canonical vocabulary — `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### TTS config

Default to Edge free TTS for local development and end-to-end testing. API-compatible
TTS must use neutral configuration names and user-facing wording. See `docs/tts-config.md`.
