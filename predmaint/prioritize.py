"""Work-order prioritizer (domain differentiator #2).

score = criticality(1-5) x failure_probability(0-1) x production_impact(1-5),
normalized to 0-100, then mapped to P1/P2/P3 bands. Every ranking shows the
factors so the order is auditable. Production impact currently equals asset
criticality (PM-PRIO-02), so in practice the score is criticality^2 x P(fail);
a separate per-line impact input is planned, not built.

A work order on an asset with no sensor readings gets band REVIEW
(PM-PRIO-03) and is listed last: the scorer cannot say it is safe.
"""

from __future__ import annotations

import sqlite3

# PM-PRIO-01: band cutoffs on the 0-100 priority score
P1_CUTOFF, P2_CUTOFF = 60.0, 30.0


def _failure_prob(conn: sqlite3.Connection, asset_id: str) -> float:
    """Use the prediction scorer's risk as the failure probability (None = no readings)."""
    from . import predict
    try:
        return predict.score_asset(conn, asset_id)["risk"]
    except ValueError:
        return None


def prioritize(conn: sqlite3.Connection) -> list[dict]:
    """Rank all open/in-progress work orders by priority score."""
    rows = conn.execute(
        "SELECT w.wo_id, w.asset_id, w.title, w.priority, w.status, w.created_day, "
        "a.criticality, a.line FROM work_orders w "
        "JOIN assets a ON w.asset_id = a.asset_id "
        "WHERE w.status != 'closed' ORDER BY w.wo_id").fetchall()
    ranked = []
    for wo_id, asset_id, title, priority, status, _created_day, crit, _line in rows:
        fprob = _failure_prob(conn, asset_id)
        impact = crit  # production impact follows asset criticality (PM-PRIO-02)
        if fprob is None:
            score, band = None, "REVIEW"  # PM-PRIO-03
        else:
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
                "failure_probability": None if fprob is None else round(fprob, 3),
                "production_impact": impact,
                "wo_priority": priority,
            },
        })
    ranked.sort(key=lambda r: (r["score"] is not None, r["score"] or 0.0), reverse=True)
    return ranked
