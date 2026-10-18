"""Thin Streamlit demo for the predictive maintenance agent.

Run:  pip install streamlit && streamlit run demo/app.py
All logic lives in predmaint/demo_helpers.py (stdlib, fully tested).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    raise SystemExit("pip install streamlit, then rerun: streamlit run demo/app.py")

from predmaint import demo_helpers, orchestrator, telemetry, views  # noqa: E402

st.title("Ironpeak Manufacturing — Reliability Operations (demo)")
st.caption("Synthetic data. Nothing here is real plant operations data.")

with st.expander("Reliability summary"):
    st.json(demo_helpers.reliability_summary())

st.subheader("Top work orders")
for wo in demo_helpers.top_work_orders(3):
    st.write(f"**{wo['wo_id']}** [{wo['band']}] {wo['title']} — score {wo['score']}")

conn = telemetry.build_db()
views.create_views(conn)
orch = orchestrator.Orchestrator(conn)

q = st.text_input("Ask about asset health, failures, work orders, or parts",
                  "Which assets are at risk of failure?")
if st.button("Ask"):
    st.json(orch.answer(q))

st.subheader("Vendor advisories")
st.json(demo_helpers.vendor_notes())
