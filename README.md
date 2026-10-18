# Jagadish-predictive-maintenance-agents

**Recruiter summary:** Unplanned downtime is the most expensive failure mode in manufacturing — and it usually announces itself weeks early in vibration and temperature trends. This repo is an end-to-end reliability-operations agent: it answers open-ended maintenance questions over synthetic telemetry, scores every asset with a transparent remaining-useful-life model, ranks the work-order backlog by criticality x failure-probability x production-impact (impact currently equals criticality), and stops line-stop recommendations and emergency work orders at a human confirmation gate. Proof: 65 regression checks green; the demo flags PUMP-101 at risk 0.772 with 41 days RUL and ranks WO-0043 (inspect pump bearings) P1 at 77.2.

## Problem → approach → outcome

**Problem.** Reliability teams drown in sensor data but starve for decisions: which asset fails next, which work order goes first, and which recommendation needs a human before it costs a shift of production.

**Approach.** A ReAct orchestrator fans out across five tools (text-to-SQL over read-only views, SOP RAG, failure-prediction scorer, work-order prioritizer, vendor advisory signal), classifies every event into T1–T4 escalation tiers, and gates T3/T4 actions on human confirmation. Every step lands in a hash-chained audit log.

**Outcome.** Deterministic, testable reliability intelligence: ask "which assets are at risk of failure?" and get the highest-risk asset with a per-feature breakdown, plus a ranked work-order plan.

## How it works

1. `predmaint/telemetry.py` builds a seeded SQLite world (fictional Kestrelmoor Manufacturing): assets, 30 days of vibration/temperature readings, work orders, downtime events, spare parts.
2. `predmaint/text2sql.py` maps questions to 5 intents → fixed SELECT templates → `views.py` gateway (SEC-SELECT-01/02/03, plus 04: views only via a SQLite authorizer) → one self-correction retry, then explicit escalation.
3. `predmaint/predict.py` scores every asset: least-squares vibration/temperature slopes + level + age → risk 0–1 → RUL days, with each feature's contribution shown (rules FM-*). An asset already past an FM-VIB-01/FM-TEMP-01 threshold is floored at risk 0.80 (FM-ALERT-01); assets without readings are listed, not scored.
4. `predmaint/prioritize.py` ranks open work orders: `100 * (criticality/5) * P(fail) * (impact/5)` → P1/P2/P3 bands, factors shown. Impact is set equal to criticality today (PM-PRIO-02); a work order on an asset with no readings gets band REVIEW (PM-PRIO-03).
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

**Boundary with energy-grid and warehouse-ops.** energy-grid flags feeders running over their load baseline and dispatches crews to outages that have already happened; it has no per-asset degradation trend or RUL. warehouse-ops plans labour and slotting inside a distribution centre and never models equipment health. This repo is the only one that predicts a failure *before* it happens and ranks maintenance work on that prediction.

## Guardrails and security controls

- SELECT-only SQL gateway with string-literal-aware write scanning (SEC-SELECT-01/02/03); only the views are readable (SEC-SELECT-04, SQLite authorizer, ADR 0001); at most 100 rows fetched
- T3/T4 confirmation gates; line stops and emergency work orders always gated; gate timeout denies
- Hash-chained audit with tamper detection (`verify_chain()`)
- PII scrubbing (email, phone incl. `(555) 123-4567`, SSN, card → placeholders) before feedback storage; dates and sensor readings are kept
- Live vendor feed raises an explicit gap instead of hallucinating advisories
- See `docs/threat-model.md` (STRIDE-lite)

## Limitations and known failures

- The RUL model is a transparent trend heuristic, illustrative — not a calibrated prognostics model; do not use for safety interlocks.
- Intent detection is regex-based; genuinely novel phrasings escalate instead of answering.
- The vendor feed is seeded/fake; the live backend is a documented stub.
- No LLM is wired in; the planner is deterministic (see interview-points for the production path).
- Production impact equals asset criticality (PM-PRIO-02), so a low-criticality asset in alarm can still rank P3 (FAN-402 forced into alarm: risk 0.80, priority score 12.8).
- Temperature *level* only enters through the FM-ALERT-01 floor, not as a weighted feature.

## Standardization review (2026-10-18)

Reviewed against the portfolio standard after the build. Bugs found and fixed, each now pinned by a test:

1. **Gateway had no view allowlist.** It blocked writes, but `SELECT * FROM assets`, a comma join, `"sqlite_master"` and `FROM/**/assets` all read base tables or the schema, and a caller-written `LIMIT 100000` (or `LIMIT 100000 -- x`) returned 1,000 rows past the 100-row cap. A SQLite authorizer (`predmaint/authz.py`, ADR 0001) now refuses any read that is not a published view (`SEC-SELECT-04`); rows past 100 are never fetched.
2. **An asset in alarm could get a long RUL.** Temperature level is not a scorer feature and vibration level is only 20%, so an asset held flat at 5.2 mm/s and 88 C fired FM-VIB-01 and FM-TEMP-01 yet scored risk 0.275, 130 days RUL, P3. New rule FM-ALERT-01 floors risk at 0.80 (36 days) whenever an FM alert fires, and the breakdown says so. Seeded results are unchanged (no seeded asset is in alarm).
3. **One asset without readings crashed the whole ranking.** `predict_all` and `prioritize` raised `ValueError` for a newly installed asset. Assets without readings are now skipped by the scorer (`assets_without_readings()` lists them) and their work orders get band REVIEW (PM-PRIO-03), listed last.
4. **PII scrubber destroyed maintenance facts.** The phone pattern matched any 10+ character digit run, so `2026-10-18` became `[PHONE]`, `readings 12 14 16 18 20 22` became `readings [PHONE]`, and `(555) 123-4567` left a stray `(`. It now uses the shared anchored phone pattern plus a card pattern (tested both ways).
5. **README overstated the prioritizer.** "Production impact" is set equal to criticality in code (PM-PRIO-02), so the score is criticality² × P(fail). The README now says so; a separate per-line impact input is listed as Planned.

Differentiator on the seeded data (regenerated and checked by CI on every push):

<!-- run: python scripts/show_differentiator.py -->
```text
Failure-prediction scorer, top 3 by risk:
  PUMP-101: risk 0.772, RUL 41 days, contrib {'vib_slope': 0.322, 'temp_slope': 0.258, 'vib_level': 0.108, 'age': 0.083}
  COMP-301: risk 0.236, RUL 138 days, contrib {'vib_slope': 0.069, 'temp_slope': 0.019, 'vib_level': 0.056, 'age': 0.092}
  AGIT-601: risk 0.132, RUL 156 days, contrib {'vib_slope': 0.019, 'temp_slope': 0.017, 'vib_level': 0.012, 'age': 0.083}
Work-order prioritizer (100 x crit/5 x P(fail) x impact/5; impact = criticality today):
  WO-0043 PUMP-101: 77.2 P1
  WO-0042 COMP-301: 23.6 P3
  WO-0039 CONV-505: 3.9 P3
  WO-0044 FAN-402: 1.6 P3

FAN-402 held flat at 5.2 mm/s and 88 C: alerts ['FM-VIB-01', 'FM-TEMP-01'], risk 0.8 (alert floor True), RUL 36 days

Gateway: SEC-SELECT-04: 'assets' is not a read-only view
```
<!-- /run -->

Test count (also checked by CI):

<!-- run: python scripts/count_tests.py -->
```text
65 tests collected
```
<!-- /run -->

## Built / Written-not-run / Planned

| Item | Status |
|---|---|
| Telemetry, 5 text-to-SQL intents, gateway | Built, 65 checks green |
| CI on every push: ruff, tests, docs drift check, hashed brand check, gitleaks; CodeQL; Dependabot | Built |
| Failure-prediction scorer (RUL + breakdown) | Built, tested incl. alert rules |
| Work-order prioritizer (P1/P2/P3) | Built, tested incl. band cutoffs |
| SOP RAG (4 docs), vendor signal (fake/live-gap) | Built, tested |
| T1–T4 escalation, confirmation gates, audit, PII-scrubbed feedback | Built, tested |
| Streamlit demo | Built (logic tested; UI not run here) |
| Separate per-line production-impact input for the prioritizer | Planned |
| Live LLM planner, real historian/CMMS feed, calibrated RUL | Planned |

## Knowledge

- [`knowledge/domain-notes.md`](knowledge/domain-notes.md) — distilled reliability-ops notes
- [`knowledge/architecture.md`](knowledge/architecture.md) — Mermaid diagrams
- [`docs/implementation-guide.md`](docs/implementation-guide.md) — adopter guide
- [`docs/interview-points.md`](docs/interview-points.md) — talk track
- [`docs/threat-model.md`](docs/threat-model.md) — STRIDE-lite
- [`docs/adr/0001-sqlite-authorizer-backstop.md`](docs/adr/0001-sqlite-authorizer-backstop.md) — gateway backstop

## Run it

```bash
python -m pytest tests/ -q          # 65 checks
python scripts/count_tests.py       # prints the real total
pip install streamlit && streamlit run demo/app.py
```

## Related repos

- [Jagadish-coldchain-logistics-agents](https://github.com/jagadishmazure-jpg/Jagadish-coldchain-logistics-agents) — same FDE spine, reefer-fleet telemetry
- [Jagadish-retail-ops-agents](https://github.com/jagadishmazure-jpg/Jagadish-retail-ops-agents) — same FDE spine, retail telemetry
- [Jagadish-energy-grid-agents](https://github.com/jagadishmazure-jpg/Jagadish-energy-grid-agents) — reacts to outages; this repo predicts failures
- [Jagadish-warehouse-ops-agents](https://github.com/jagadishmazure-jpg/Jagadish-warehouse-ops-agents) — DC operations, no equipment health

*All data is synthetic and fictional. This project is an independent portfolio build, unaffiliated with any employer or vendor.*
