"""Stdlib-only demo helpers (fully tested); demo/app.py is the thin UI layer."""

from __future__ import annotations

from . import predict, prioritize, telemetry, text2sql, vendorsignal, views


def reliability_summary() -> dict:
    """One-call plant summary used by the demo and README excerpts."""
    conn = telemetry.build_db()
    views.create_views(conn)
    scored = predict.predict_all(conn)
    worst = scored[0]
    backlog = text2sql.run_question(conn, "show the work order backlog")
    downtime = text2sql.run_question(conn, "downtime by line")
    parts = text2sql.run_question(conn, "which parts are below reorder")
    return {
        "highest_risk_asset": worst["asset_id"],
        "risk": worst["risk"],
        "rul_days": worst["rul_days"],
        "open_work_orders": backlog["row_count"],
        "worst_line": downtime["rows"][0]["line"] if downtime["rows"] else None,
        "parts_below_reorder": [r["part_id"] for r in parts["rows"]
                                if r["status"] == "below-reorder"],
    }


def top_work_orders(n: int = 3) -> list[dict]:
    conn = telemetry.build_db()
    views.create_views(conn)
    return prioritize.prioritize(conn)[:n]


def vendor_notes(asset_type: str = "centrifugal pump") -> list[dict]:
    return vendorsignal.FakeVendorFeed().advisories(asset_type)
