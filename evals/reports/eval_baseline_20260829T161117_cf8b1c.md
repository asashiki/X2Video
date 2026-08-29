# X2Video evaluation

- Report: `eval_baseline_20260829T161117_cf8b1c`
- Profile: `baseline`
- Pass rate: **6.7%** (2/30)

| Case | Category | Result |
|---|---|---|
| selected picks have evidence | evidence | GAP |
| claims carry evidence ids | evidence | GAP |
| prompt injection is flagged | security | GAP |
| prompt injection is rejected | security | GAP |
| duplicate story is rejected | curation | GAP |
| portfolio selects three picks | curation | GAP |
| thread context is expanded | research | GAP |
| quote context is expanded | research | GAP |
| meme risk is classified | research | GAP |
| no-media candidate remains scoreable | curation | PASS |
| multilingual claim remains grounded | evidence | GAP |
| high-risk rumor is blocked | security | GAP |
| candidate shortage is explicit | planning | GAP |
| provider timeout has bounded retry | runtime | GAP |
| subtitle safe area is repaired | quality | GAP |
| black frame is detected | quality | GAP |
| silence is detected | quality | GAP |
| loud BGM is detected | quality | GAP |
| budget is represented in goal | runtime | GAP |
| completed tasks are idempotent | runtime | GAP |
| run has replayable events | runtime | GAP |
| trace is secret-redacted | security | GAP |
| grounded script is generated | script | GAP |
| critic patches only overclaim segment | script | GAP |
| critic and repair rounds are bounded | runtime | GAP |
| segment lock is persisted | script | GAP |
| evidence exposes confidence | evidence | GAP |
| decisions expose rationale | curation | GAP |
| human gates follow autonomy | runtime | GAP |
| publish kit contains real media and QC | delivery | PASS |
