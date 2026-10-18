"""Failure-prediction scorer (domain differentiator #1).

A transparent trend model over vibration + temperature readings:
each feature's contribution is shown, so a predicted failure is always
explainable. Simplified and illustrative — not a substitute for a real
prognostics model. All thresholds are documented below (rules FM-*).
"""

from __future__ import annotations

import sqlite3

# FM-VIB-01: vibration alert threshold (mm/s) for rotating equipment
VIB_ALERT = 4.5
# FM-TEMP-01: temperature alert threshold (C) for pump/motor bearings
TEMP_ALERT = 85.0
# FM-RUL-01: features and weights for the risk score (sum to 1.0)
W_VIB_SLOPE, W_TEMP_SLOPE, W_VIB_LEVEL, W_AGE = 0.40, 0.30, 0.20, 0.10
# FM-RUL-02: baseline horizon (days) scaled by (1 - risk)
BASE_HORIZON_DAYS = 180
# FM-ALERT-01: an asset already past an FM-VIB-01/FM-TEMP-01 threshold is at
# least this risky, whatever its trend (a flat line at alarm level is not safe)
ALERT_RISK_FLOOR = 0.80
CURRENT_YEAR = 2026


def _slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of y over x."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom


def _norm(value: float, lo: float, hi: float) -> float:
    if hi <= lo:
        return 0.0
    return max(0.0, min(1.0, (value - lo) / (hi - lo)))


def score_asset(conn: sqlite3.Connection, asset_id: str,
                window_days: int = 14) -> dict:
    """Score one asset; return risk, RUL estimate, and the feature breakdown."""
    rows = conn.execute(
        "SELECT day, vibration_mm_s, temp_c FROM sensor_readings "
        "WHERE asset_id = ? ORDER BY day DESC LIMIT ?",
        (asset_id, window_days)).fetchall()
    if not rows:
        raise ValueError(f"no readings for asset {asset_id!r}")
    rows = rows[::-1]  # chronological
    days = [r[0] for r in rows]
    vibs = [r[1] for r in rows]
    temps = [r[2] for r in rows]

    vib_slope = _slope(days, vibs)
    temp_slope = _slope(days, temps)
    vib_level = vibs[-1]
    info = conn.execute(
        "SELECT install_year FROM assets WHERE asset_id = ?", (asset_id,)).fetchone()
    age = CURRENT_YEAR - info[0] if info else 0

    f_vib_slope = _norm(vib_slope, 0.0, 0.05)
    f_temp_slope = _norm(temp_slope, 0.0, 0.4)
    f_vib_level = _norm(vib_level, 2.0, VIB_ALERT)
    f_age = _norm(age, 0, 12)

    risk = (W_VIB_SLOPE * f_vib_slope + W_TEMP_SLOPE * f_temp_slope
            + W_VIB_LEVEL * f_vib_level + W_AGE * f_age)
    alerts = [r for r in (("FM-VIB-01", vib_level >= VIB_ALERT),
                          ("FM-TEMP-01", temps[-1] >= TEMP_ALERT)) if r[1]]
    floor_applied = bool(alerts) and risk < ALERT_RISK_FLOOR
    if floor_applied:
        risk = ALERT_RISK_FLOOR
    rul_days = max(1, round(BASE_HORIZON_DAYS * (1.0 - risk)))
    return {
        "asset_id": asset_id,
        "risk": round(risk, 3),
        "rul_days": rul_days,
        "breakdown": {
            "vib_slope_per_day": round(vib_slope, 4),
            "temp_slope_per_day": round(temp_slope, 3),
            "latest_vib_mm_s": round(vib_level, 3),
            "age_years": age,
            "contrib": {
                "vib_slope": round(W_VIB_SLOPE * f_vib_slope, 3),
                "temp_slope": round(W_TEMP_SLOPE * f_temp_slope, 3),
                "vib_level": round(W_VIB_LEVEL * f_vib_level, 3),
                "age": round(W_AGE * f_age, 3),
            },
            "alert_floor": floor_applied,  # FM-ALERT-01
        },
        "alerts": alerts,
    }


def predict_all(conn: sqlite3.Connection) -> list[dict]:
    """Score every asset with readings; return sorted by risk (highest first).

    Assets with no readings yet (e.g. newly installed) are skipped instead of
    failing the whole ranking; ``assets_without_readings`` lists them.
    """
    assets = [r[0] for r in conn.execute(
        "SELECT asset_id FROM assets WHERE asset_id IN (SELECT asset_id FROM sensor_readings)")]
    scored = [score_asset(conn, a) for a in assets]
    scored.sort(key=lambda s: s["risk"], reverse=True)
    return scored


def assets_without_readings(conn: sqlite3.Connection) -> list[str]:
    """Assets the scorer cannot assess yet (no sensor readings)."""
    return [r[0] for r in conn.execute(
        "SELECT asset_id FROM assets WHERE asset_id NOT IN "
        "(SELECT asset_id FROM sensor_readings) ORDER BY asset_id")]
