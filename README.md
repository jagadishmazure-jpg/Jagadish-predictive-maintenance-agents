# Jagadish-predictive-maintenance-agents

**Recruiter summary:** Unplanned downtime is the most expensive failure mode in manufacturing — and it usually announces itself weeks early in vibration and temperature trends. This repo is an end-to-end reliability-operations agent: it answers open-ended maintenance questions over synthetic telemetry, scores every asset with a transparent remaining-useful-life model, ranks the work-order backlog by criticality x failure-probability x production-impact, and stops line-stop recommendations and emergency work orders at a human confirmation gate. Proof: 43 regression checks green; the demo flags PUMP-101 at risk 0.772 with 41 days RUL and ranks WO-0043 (inspect pump bearings) P1 at 77.2.

## Problem → approach → outcome

**Problem.** Reliability teams drown in sensor data but starve for decisions: which asset fails next, which work order goes first, and which recommendation needs a human before it costs a shift of production.

**Approach.** A ReAct orchestrator fans out across five tools (text-to-SQL over read-only views, SOP RAG, failure-prediction scorer, work-order prioritizer, vendor advisory signal), classifies every event into T1–T4 escalation tiers, and gates T3/T4 actions on human confirmation. Every step lands in a hash-chained audit log.

**Outcome.** Deterministic, testable reliability intelligence: ask "which assets are at risk of failure?" and get the highest-risk asset with a per-feature breakdown, plus a ranked work-order plan.

## How it works

1. `predmaint/telemetry.py` builds a seeded SQLite world (fictional Ironpeak Manufacturing): assets, 30 days of vibration/temperature readings, work orders, downtime events, spare parts.
2. `predmaint/text2sql.py` maps questions to 5 intents → fixed SELECT templates → `views.py` gateway (SEC-SELECT-01/02/03) → one self-correction retry, then explicit escalation.
3. `predmaint/predict.py` scores every asset: least-squares vibration/temperature slopes + level + age → risk 0–1 → RUL days, with each feature's contribution shown (rules FM-*).
4. `predmaint/prioritize.py` ranks open work orders: `100 * (criticality/5) * P(fail) * (impact/5)` → P1/P2/P3 bands, factors shown.
5. `predmaint/sop_rag.py` retrieves SOP sections with `file §section` citations; says so when nothing matches.
6. `predmaint/vendorsignal.py` serves seeded vendor advisories; the live backend reports an explicit gap instead of hallucinating.
7. `predmaint/escalation.py` tiers events; line stops and emergency work orders always need confirmation.
8. `predmaint/audit.py` + `predmaint/feedback.py` record everything tamper-evidently; feedback text is PII-scrubbed first.

Real run (seed 42):

```
>>> from predmaint import demo_helpers
>>> demo_helpers.reliability_summary()
{'highest_risk_asset': 'PUMP-101', 'risk': 0.772, 'rul_days': 41,
 'open_work_orders': 4, 'worst_line': 'LINE-B',
 'parts_below_reorder': ['BRG-6205']}
>>> demo_helpers.top_work_orders(1)[0]['wo_id']
'WO-0043'
```

## How this differs from coldchain/retail

Same FDE spine (SQLite telemetry, text-to-SQL, SOP RAG, escalation, audit), but the domain machinery is reliability-specific: a **failure-prediction scorer** (vibration/temperature trend features → RUL with a transparent breakdown — meaningless outside rotating equipment) and a **work-order prioritizer** (criticality x failure-probability x production-impact ranking). Cold-chain optimizes for temperature compliance; retail for demand signals; this repo optimizes for *planned maintenance before unplanned downtime*.

## Guardrails and security controls

- SELECT-only SQL gateway with string-literal-aware write scanning (SEC-SELECT-01/02/03)
- T3/T4 confirmation gates; line stops and emergency work orders always gated; gate timeout denies
- Hash-chained audit with tamper detection (`verify_chain()`)
- PII scrubbing (email/phone/SSN → placeholders) before feedback storage
- Live vendor feed raises an explicit gap instead of hallucinating advisories
- See `docs/threat-model.md` (STRIDE-lite)

## Limitations and known failures

- The RUL model is a transparent trend heuristic, illustrative — not a calibrated prognostics model; do not use for safety interlocks.
- Intent detection is regex-based; genuinely novel phrasings escalate instead of answering.
- The vendor feed is seeded/fake; the live backend is a documented stub.
- No LLM is wired in; the planner is deterministic (see interview-points for the production path).

## Built / Written-not-run / Planned

| Item | Status |
|---|---|
| Telemetry, 5 text-to-SQL intents, gateway | Built, 43 checks green |
| Failure-prediction scorer (RUL + breakdown) | Built, tested incl. alert rules |
| Work-order prioritizer (P1/P2/P3) | Built, tested incl. band cutoffs |
| SOP RAG (4 docs), vendor signal (fake/live-gap) | Built, tested |
| T1–T4 escalation, confirmation gates, audit, PII-scrubbed feedback | Built, tested |
| Streamlit demo | Built (logic tested; UI not run here) |
| Live LLM planner, real historian/CMMS feed, calibrated RUL | Planned |

## Knowledge

- [`knowledge/domain-notes.md`](knowledge/domain-notes.md) — distilled reliability-ops notes
- [`knowledge/architecture.md`](knowledge/architecture.md) — Mermaid diagrams
- [`docs/implementation-guide.md`](docs/implementation-guide.md) — adopter guide
- [`docs/interview-points.md`](docs/interview-points.md) — talk track
- [`docs/threat-model.md`](docs/threat-model.md) — STRIDE-lite

## Run it

```bash
python -m pytest tests/ -q          # 43 checks, ~0.3s
python scripts/count_tests.py       # prints the real total
pip install streamlit && streamlit run demo/app.py
```

## Related repos

- [Jagadish-coldchain-logistics-agents](https://github.com/jagadishmazure-jpg/Jagadish-coldchain-logistics-agents) — same FDE spine, reefer-fleet telemetry
- [Jagadish-retail-ops-agents](https://github.com/jagadishmazure-jpg/Jagadish-retail-ops-agents) — same FDE spine, retail telemetry

*All data is synthetic and fictional. This project is an independent portfolio build, unaffiliated with any employer or vendor.*
