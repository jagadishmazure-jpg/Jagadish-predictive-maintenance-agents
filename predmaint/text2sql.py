"""Intent detection + fixed SELECT templates over the read-only views.

One simplified-query retry on failure, then an explicit EscalationNeeded
instead of a guessed answer.
"""

from __future__ import annotations

import re
import sqlite3

from . import views


class EscalationNeeded(Exception):
    """Raised when no intent matches or a query fails after one retry."""


_INTENTS = [
    ("asset_health",
     re.compile(r"health|condition|which assets|asset status", re.I),
     "SELECT asset_id, asset_type, line, criticality, avg_vib, avg_temp "
     "FROM v_asset_health ORDER BY avg_vib DESC"),
    ("predicted_failures",
     re.compile(r"fail|predict|risk|rul|remaining", re.I),
     "SELECT asset_id, asset_type, line, criticality "
     "FROM v_predicted_failures ORDER BY criticality DESC"),
    ("workorder_backlog",
     re.compile(r"work order|backlog|maintenance queue|open wo", re.I),
     "SELECT wo_id, asset_id, title, priority, status FROM v_workorder_backlog "
     "ORDER BY created_day"),
    ("downtime_by_line",
     re.compile(r"downtime|line stop|availability by line", re.I),
     "SELECT line, events, total_h, avg_h FROM v_downtime_by_line "
     "ORDER BY total_h DESC"),
    ("parts_availability",
     re.compile(r"part|spare|stock|reorder|inventory", re.I),
     "SELECT part_id, qty_on_hand, reorder_point, status FROM v_parts_availability "
     "ORDER BY qty_on_hand"),
]


def detect_intent(question: str) -> str | None:
    for name, pattern, _ in _INTENTS:
        if pattern.search(question):
            return name
    return None


def _template(name: str) -> str:
    for n, _, sql in _INTENTS:
        if n == name:
            return sql
    raise KeyError(name)


def run_question(conn: sqlite3.Connection, question: str) -> dict:
    """Answer *question*; retry once simplified, else escalate."""
    intent = detect_intent(question)
    if intent is None:
        raise EscalationNeeded(f"no intent matched: {question!r}")
    sql = _template(intent)
    try:
        rows = views.run_query(conn, sql)
    except Exception:
        # One simplified retry: drop the ORDER BY, keep the projection.
        simple = sql.split(" ORDER BY")[0]
        try:
            rows = views.run_query(conn, simple)
        except Exception as exc:
            raise EscalationNeeded(f"query failed after retry: {exc}") from exc
    return {"intent": intent, "rows": rows, "row_count": len(rows)}
