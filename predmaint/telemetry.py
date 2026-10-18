"""Synthetic reliability telemetry (SQLite), deterministic with seed 42.

Fictional plant: Kestrelmoor Manufacturing. Assets emit vibration (mm/s) and
temperature (C) readings with deterministic trends — one pump is degrading,
the rest are stable. All names and brands are invented.
"""

from __future__ import annotations

import random
import sqlite3

SEED = 42

# Deterministic anchors (used by tests and demo):
ANCHOR_DEGRADING_ASSET = "PUMP-101"      # rising vibration + temp -> predicted failure
ANCHOR_OPEN_WO = "WO-0042"               # open high-priority WO on COMP-301
ANCHOR_DOWNTIME_LINE = "LINE-B"          # line with the longest recorded downtime
ANCHOR_LOW_PART = "BRG-6205"             # bearing below reorder point

_ASSETS = [
    # asset_id, asset_type, line, install_year, criticality (1-5)
    ("PUMP-101", "centrifugal pump", "LINE-A", 2016, 5),
    ("PUMP-102", "centrifugal pump", "LINE-A", 2019, 4),
    ("MOTOR-204", "induction motor", "LINE-A", 2018, 4),
    ("COMP-301", "air compressor", "LINE-B", 2015, 5),
    ("COMP-302", "air compressor", "LINE-B", 2020, 3),
    ("FAN-402", "exhaust fan", "LINE-B", 2017, 2),
    ("CONV-505", "belt conveyor", "LINE-C", 2019, 3),
    ("CONV-506", "belt conveyor", "LINE-C", 2021, 2),
    ("AGIT-601", "mixer agitator", "LINE-C", 2016, 4),
    ("VALVE-701", "control valve", "LINE-A", 2020, 2),
]

# Per-asset sensor behavior: (base_vib, vib_trend_per_day, base_temp, temp_trend_per_day)
_SENSOR_PROFILE = {
    "PUMP-101": (2.1, 0.045, 62.0, 0.35),   # degrading
    "PUMP-102": (1.8, 0.002, 58.0, 0.02),
    "MOTOR-204": (1.5, 0.001, 66.0, 0.01),
    "COMP-301": (2.4, 0.010, 71.0, 0.05),   # mildly elevated
    "COMP-302": (1.9, 0.002, 68.0, 0.02),
    "FAN-402": (1.2, 0.001, 54.0, 0.01),
    "CONV-505": (1.6, 0.003, 49.0, 0.02),
    "CONV-506": (1.4, 0.001, 48.0, 0.01),
    "AGIT-601": (2.0, 0.004, 60.0, 0.03),
    "VALVE-701": (0.9, 0.000, 45.0, 0.00),
}

_WORK_ORDERS = [
    # wo_id, asset_id, title, priority, status, created_day
    ("WO-0042", "COMP-301", "Replace compressor seals", "high", "open", 28),
    ("WO-0043", "PUMP-101", "Inspect pump bearings", "high", "open", 29),
    ("WO-0044", "FAN-402", "Clean fan housing", "low", "open", 25),
    ("WO-0039", "CONV-505", "Re-tension belt", "medium", "in-progress", 22),
    ("WO-0031", "MOTOR-204", "Lubricate motor bearings", "medium", "closed", 10),
    ("WO-0028", "PUMP-102", "Check coupling alignment", "low", "closed", 8),
]

_DOWNTIME = [
    # asset_id, line, start_day, duration_h, cause
    ("COMP-301", "LINE-B", 12, 6.0, "seal leak"),
    ("CONV-505", "LINE-C", 18, 2.5, "belt slip"),
    ("PUMP-101", "LINE-A", 26, 1.5, "vibration trip"),
]

_PARTS = [
    # part_id, asset_type, qty_on_hand, reorder_point, lead_time_days
    ("BRG-6205", "centrifugal pump", 2, 6, 14),
    ("SEAL-KIT-88", "air compressor", 4, 4, 21),
    ("BELT-X4", "belt conveyor", 10, 5, 7),
    ("FILTER-10M", "exhaust fan", 12, 6, 10),
]


def build_db(days: int = 30) -> sqlite3.Connection:
    """Build the seeded SQLite world; return an open in-memory connection."""
    rng = random.Random(SEED)
    conn = sqlite3.connect(":memory:")
    conn.execute("""CREATE TABLE assets (
        asset_id TEXT PRIMARY KEY, asset_type TEXT, line TEXT,
        install_year INTEGER, criticality INTEGER)""")
    conn.execute("""CREATE TABLE sensor_readings (
        asset_id TEXT, day INTEGER, vibration_mm_s REAL, temp_c REAL)""")
    conn.execute("""CREATE TABLE work_orders (
        wo_id TEXT PRIMARY KEY, asset_id TEXT, title TEXT,
        priority TEXT, status TEXT, created_day INTEGER)""")
    conn.execute("""CREATE TABLE downtime_events (
        asset_id TEXT, line TEXT, start_day INTEGER,
        duration_h REAL, cause TEXT)""")
    conn.execute("""CREATE TABLE spare_parts (
        part_id TEXT PRIMARY KEY, asset_type TEXT,
        qty_on_hand INTEGER, reorder_point INTEGER, lead_time_days INTEGER)""")

    for row in _ASSETS:
        conn.execute("INSERT INTO assets VALUES (?,?,?,?,?)", row)

    for asset_id, (bv, vt, bt, tt) in _SENSOR_PROFILE.items():
        for day in range(days):
            vib = bv + vt * day + rng.uniform(-0.08, 0.08)
            temp = bt + tt * day + rng.uniform(-0.6, 0.6)
            conn.execute(
                "INSERT INTO sensor_readings VALUES (?,?,?,?)",
                (asset_id, day, round(vib, 3), round(temp, 2)))

    for row in _WORK_ORDERS:
        conn.execute("INSERT INTO work_orders VALUES (?,?,?,?,?,?)", row)
    for row in _DOWNTIME:
        conn.execute("INSERT INTO downtime_events VALUES (?,?,?,?,?)", row)
    for row in _PARTS:
        conn.execute("INSERT INTO spare_parts VALUES (?,?,?,?,?)", row)
    conn.commit()
    return conn
