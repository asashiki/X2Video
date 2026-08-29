# Three-minute Agent Studio demo

This script uses frozen, public-safe fixtures. Start with `x2video studio`, open `http://127.0.0.1:8765`, then keep the QC and Eval reports ready.

## 0:00–0:20 — Intent

Create an Auto Run with: “做一条 60 秒以内的今日 AI 新闻，三条以内，避免重复，优先可信信息。” Show the generated format, audience, budget and bounded task plan.

## 0:20–0:50 — Evidence and portfolio

Open Curation. Three high-confidence Picks have Claims and sources. One instruction-like rumor and one duplicate are rejected with explicit risks and alternatives. Reorder a Pick or request more research; the action is appended to Trace.

## 0:50–1:20 — Human control

For an Assisted Run, approve or reject the waiting Gate. Demonstrate Pause, Replay and Fork. Replay reads the durable event log without repeating side effects.

## 1:20–1:50 — Grounded Script

Open Script/Storyboard. The fixture deliberately changes “逐步开放” into unsupported “全面开放.” Script Critic records one typed issue and patches only Segment 02. Show revision `r2`, Evidence ID, PATCHED marker and the unchanged locked segments.

## 1:50–2:25 — Real render and repair

Open QC Lab. Play the real 1080×1920 MP4. `qc.before.json` contains an actual safe-area violation (`1810 > 1680`) plus FFmpeg black-frame, silence and loudness diagnostics. Auto Repair changes only the declared subtitle constraint to `1620`, rerenders, and `qc.after.json` passes regression in one of two allowed rounds.

## 2:25–3:00 — Proof

Show Timeline cost and latency, the redacted JSONL Trace, Golden Publish Kit, Memory approval, and the fixed 30-case comparison report. State the scope precisely: the Demo is offline and deterministic; official X MCP and real benchmark distillation remain separate source-data work.
