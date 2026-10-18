"""Read-only views plus a SELECT-only SQL gateway with cited rule IDs.

SEC-SELECT-01: only SELECT statements may run.
SEC-SELECT-02: write keywords (INSERT/UPDATE/DELETE/DROP/...) are rejected;
    the scan is string-literal aware so words inside quotes don't false-positive.
SEC-SELECT-03: at most 100 rows are returned; rows past the cap are never
    fetched, whatever LIMIT the caller wrote.
SEC-SELECT-04: only the read-only views may be read. Enforced by a SQLite
    authorizer (predmaint/authz.py, ADR 0001), so comma joins, quoted names
    and comments cannot reach base tables or sqlite_master.
"""

from __future__ import annotations

import re
import sqlite3

from . import authz

MAX_ROWS = 100

VIEW_DDLS = {
    "v_asset_health": """
        CREATE VIEW v_asset_health AS
        SELECT a.asset_id, a.asset_type, a.line, a.criticality,
               ROUND(AVG(s.vibration_mm_s), 3) AS avg_vib,
               ROUND(AVG(s.temp_c), 1) AS avg_temp,
               COUNT(s.day) AS readings
        FROM assets a JOIN sensor_readings s ON a.asset_id = s.asset_id
        GROUP BY a.asset_id
    """,
    "v_predicted_failures": """
        CREATE VIEW v_predicted_failures AS
        SELECT asset_id, asset_type, line, criticality
        FROM assets WHERE criticality >= 4
    """,
    "v_workorder_backlog": """
        CREATE VIEW v_workorder_backlog AS
        SELECT wo_id, asset_id, title, priority, status, created_day
        FROM work_orders WHERE status != 'closed'
    """,
    "v_downtime_by_line": """
        CREATE VIEW v_downtime_by_line AS
        SELECT line, COUNT(*) AS events, ROUND(SUM(duration_h), 1) AS total_h,
               ROUND(AVG(duration_h), 1) AS avg_h
        FROM downtime_events GROUP BY line
    """,
    "v_parts_availability": """
        CREATE VIEW v_parts_availability AS
        SELECT part_id, asset_type, qty_on_hand, reorder_point, lead_time_days,
               CASE WHEN qty_on_hand < reorder_point THEN 'below-reorder' ELSE 'ok' END AS status
        FROM spare_parts
    """,
}

WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|GRANT|ATTACH|DETACH)\b",
    re.IGNORECASE,
)
_LITERAL = re.compile(r"'(?:[^']|'')*'")


class GatewayError(ValueError):
    """Raised when a query violates the SELECT-only gateway."""


def _strip_literals(sql: str) -> str:
    return _LITERAL.sub("''", sql)


def ensure_select_only(sql: str, max_rows: int = 100) -> str:
    """Validate *sql* against the gateway rules; return a LIMIT-capped query."""
    cleaned = sql.strip().rstrip(";")
    if not re.match(r"(?i)^\s*select\b", cleaned):
        raise GatewayError("SEC-SELECT-01: only SELECT statements are allowed")
    if WRITE_KEYWORDS.search(_strip_literals(cleaned)):
        raise GatewayError("SEC-SELECT-02: write statements are not allowed")
    if not re.search(r"(?i)\blimit\b", _strip_literals(cleaned)):
        cleaned = f"{cleaned} LIMIT {max_rows}"  # SEC-SELECT-03 (also enforced at fetch)
    return cleaned


def create_views(conn: sqlite3.Connection) -> None:
    for ddl in VIEW_DDLS.values():
        conn.execute(ddl.replace("CREATE VIEW", "CREATE VIEW IF NOT EXISTS", 1))
    conn.commit()


def run_query(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    """Run a gateway-checked SELECT; return rows as dicts."""
    safe = ensure_select_only(sql)
    with authz.views_only(conn, VIEW_DDLS) as denied:
        try:
            cur = conn.execute(safe, params)
        except sqlite3.DatabaseError:
            if denied:
                raise GatewayError(
                    f"SEC-SELECT-04: '{denied[0]}' is not a read-only view") from None
            raise
        cols = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS)  # SEC-SELECT-03
    return [dict(zip(cols, row)) for row in rows]
