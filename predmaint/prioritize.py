"""Work-order prioritizer (domain differentiator #2).

score = criticality(1-5) x failure_probability(0-1) x production_impact(1-5),
normalized to 0-100, then mapped to P1/P2/P3 bands. Every ranking shows the
three factors so the order is auditable.
"""

from __future__ import annotations

import sqlite3

# PM-PRIO-01: band cutoffs on the 0-100 priority score
P1_CUTOFF, P2_CUTOFF = 60.0, 30.0

_PRIORITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


def _failure_prob(conn: sqlite3.Connection, asset_id: str) -> float:
    """Use the prediction scorer's risk as the failure probability."""
    from . import predict
    return predict.score_asset(conn, asset_id)["risk"]


def prioritize(conn: sqlite3.Connection) -> list[dict]:
    """Rank all open/in-progress work orders by priority score."""
    rows = conn.execute(
        "SELECT w.wo_id, w.asset_id, w.title, w.priority, w.status, w.created_day, "
        "a.criticality, a.line FROM work_orders w "
        "JOIN assets a ON w.asset_id = a.asset_id "
        "WHERE w.status != 'closed' ORDER BY w.wo_id").fetchall()
    ranked = []
    for wo_id, asset_id, title, priority, status, created_day, crit, line in rows:
        fprob = _failure_prob(conn, asset_id)
        impact = crit  # production impact follows asset criticality (PM-PRIO-02)
        score = round(100.0 * (crit / 5.0) * fprob * (impact / 5.0), 1)
        band = "P1" if score >= P1_CUTOFF else ("P2" if score >= P2_CUTOFF else "P3")
        ranked.append({
            "wo_id": wo_id,
            "asset_id": asset_id,
            "title": title,
            "status": status,
            "score": score,
            "band": band,
            "factors": {
                "criticality": crit,
                "failure_probability": round(fprob, 3),
                "production_impact": impact,
                "wo_priority": priority,
            },
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return ranked
