# Implementation guide

For adopters wiring this into a real plant.

## Offline first
Everything runs on stdlib + SQLite. `python -m pytest tests/` is the whole
build. The Streamlit demo is optional (`pip install streamlit`).

## Going live, in order
1. Replace `telemetry.build_db()` with your historian/CMMS extracts. Keep the
   table shapes; the views and intents don't care where rows come from.
2. Swap `FakeVendorFeed` for your vendor API in `vendorsignal.py`. The live
   stub already defines the gap contract — return advisories, not prose.
3. Calibrate the FM-* thresholds against your failure history before trusting
   RUL numbers; the defaults are illustrative.
4. Wire the confirmation gate to your actual approval workflow (work-order
   system, paging). Never auto-approve T4.
5. Feed real feedback through `feedback.py`; the PII scrubber runs first.

## What not to do
- Don't use the RUL score for safety-critical interlocks. It's a planning
  aid; protection systems stay hard-wired.
- Don't widen the SQL gateway. The agent asks; it never writes.
