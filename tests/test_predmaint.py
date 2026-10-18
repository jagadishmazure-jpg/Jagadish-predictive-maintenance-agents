"""Regression checks for Jagadish-predictive-maintenance-agents (synthetic data)."""

import sqlite3

import pytest

from predmaint import (
    audit,
    demo_helpers,
    escalation,
    feedback,
    orchestrator,
    pii,
    predict,
    prioritize,
    sop_rag,
    telemetry,
    text2sql,
    vendorsignal,
    views,
)


def fresh_conn():
    conn = telemetry.build_db()
    views.create_views(conn)
    return conn


# ---------- telemetry ----------

def test_seed_anchors_present():
    conn = fresh_conn()
    assert conn.execute(
        "SELECT status FROM work_orders WHERE wo_id='WO-0042'").fetchone()[0] == "open"
    assert conn.execute(
        "SELECT qty_on_hand FROM spare_parts WHERE part_id='BRG-6205'").fetchone()[0] == 2
    n = conn.execute("SELECT COUNT(*) FROM sensor_readings").fetchone()[0]
    assert n == 10 * 30


def test_telemetry_deterministic():
    c1, c2 = telemetry.build_db(), telemetry.build_db()
    q = "SELECT AVG(vibration_mm_s) FROM sensor_readings WHERE asset_id='PUMP-101'"
    assert c1.execute(q).fetchone()[0] == c2.execute(q).fetchone()[0]


def test_degrading_asset_trends_up():
    conn = fresh_conn()
    rows = conn.execute(
        "SELECT vibration_mm_s FROM sensor_readings WHERE asset_id='PUMP-101' "
        "ORDER BY day").fetchall()
    assert rows[-1][0] > rows[0][0] + 0.5  # clear upward trend


def test_fictional_names_only():
    conn = fresh_conn()
    names = " ".join(r[0] for r in conn.execute("SELECT asset_id FROM assets"))
    for real in ("Siemens", "SKF", "ABB", "Emerson", "Honeywell"):
        assert real not in names


# ---------- gateway ----------

def test_select_only_blocks_writes():
    with pytest.raises(views.GatewayError):
        views.ensure_select_only("DELETE FROM assets")


def test_gateway_blocks_write_in_subquery():
    with pytest.raises(views.GatewayError):
        views.ensure_select_only("SELECT * FROM assets WHERE 1=1; DROP TABLE x")


def test_gateway_allows_keyword_inside_string_literal():
    q = views.ensure_select_only("SELECT * FROM assets WHERE asset_id='DELETE-ME'")
    assert "DELETE-ME" in q


def test_gateway_adds_limit():
    q = views.ensure_select_only("SELECT * FROM assets")
    assert q.upper().endswith("LIMIT 100")


def test_gateway_rejects_non_select():
    with pytest.raises(views.GatewayError):
        views.ensure_select_only("UPDATE assets SET line='X'")


# ---------- text2sql ----------

def test_intent_detection():
    assert text2sql.detect_intent("which assets are unhealthy?") == "asset_health"
    assert text2sql.detect_intent("predict failures this month") == "predicted_failures"
    assert text2sql.detect_intent("work order backlog") == "workorder_backlog"
    assert text2sql.detect_intent("downtime by line") == "downtime_by_line"
    assert text2sql.detect_intent("spare parts below reorder") == "parts_availability"
    assert text2sql.detect_intent("what is the meaning of life") is None


def test_run_question_returns_rows():
    conn = fresh_conn()
    out = text2sql.run_question(conn, "show downtime by line")
    assert out["intent"] == "downtime_by_line"
    assert out["row_count"] == 3
    lines = {r["line"] for r in out["rows"]}
    assert lines == {"LINE-A", "LINE-B", "LINE-C"}


def test_run_question_escalates_on_unknown():
    conn = fresh_conn()
    with pytest.raises(text2sql.EscalationNeeded):
        text2sql.run_question(conn, "sing me a song about bearings")


def test_run_question_simplified_retry(monkeypatch):
    conn = fresh_conn()
    calls = {"n": 0}
    real_run = views.run_query

    def flaky(c, sql, params=()):
        calls["n"] += 1
        if "ORDER BY" in sql and calls["n"] == 1:
            raise sqlite3.OperationalError("boom")
        return real_run(c, sql, params)

    monkeypatch.setattr(views, "run_query", flaky)
    out = text2sql.run_question(conn, "downtime by line")
    assert out["row_count"] == 3 and calls["n"] == 2


# ---------- predict ----------

def test_predict_flags_degrading_asset():
    conn = fresh_conn()
    scored = predict.predict_all(conn)
    assert scored[0]["asset_id"] == "PUMP-101"
    assert scored[0]["risk"] > 0.5


def test_predict_breakdown_sums():
    conn = fresh_conn()
    s = predict.score_asset(conn, "PUMP-101")
    contrib = s["breakdown"]["contrib"]
    assert abs(sum(contrib.values()) - s["risk"]) < 0.01
    assert s["breakdown"]["vib_slope_per_day"] > 0.02


def test_predict_stable_asset_low_risk():
    conn = fresh_conn()
    s = predict.score_asset(conn, "VALVE-701")
    assert s["risk"] < 0.2
    assert s["rul_days"] > 100


def test_predict_rul_bounded():
    conn = fresh_conn()
    for s in predict.predict_all(conn):
        assert 1 <= s["rul_days"] <= 180


def test_predict_unknown_asset():
    conn = fresh_conn()
    with pytest.raises(ValueError):
        predict.score_asset(conn, "NOPE-999")


def test_predict_alerts_fire():
    conn = fresh_conn()
    s = predict.score_asset(conn, "PUMP-101")
    assert any(rule == "FM-VIB-01" for rule, _ in s["alerts"]) or s["risk"] > 0.4


# ---------- prioritize ----------

def test_prioritize_ranks_open_orders():
    conn = fresh_conn()
    ranked = prioritize.prioritize(conn)
    assert len(ranked) == 4  # 4 non-closed work orders
    scores = [r["score"] for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_prioritize_top_is_critical_degrading():
    conn = fresh_conn()
    ranked = prioritize.prioritize(conn)
    top = ranked[0]
    assert top["band"] == "P1"
    assert top["factors"]["criticality"] >= 4


def test_prioritize_bands_valid():
    conn = fresh_conn()
    for r in prioritize.prioritize(conn):
        assert r["band"] in ("P1", "P2", "P3")
        assert 0.0 <= r["score"] <= 100.0


# ---------- sop rag ----------

def test_rag_retrieves_with_citation():
    out = sop_rag.retrieve("how do I trend vibration readings?")
    assert out["found"]
    assert out["hits"][0]["citation"].startswith("sop-01-condition-monitoring.md")


def test_rag_not_found():
    out = sop_rag.retrieve("quantum cryptography key exchange")
    assert not out["found"]
    assert "reason" in out


# ---------- vendor signal ----------

def test_fake_vendor_feed_deterministic():
    f1 = vendorsignal.FakeVendorFeed()
    f2 = vendorsignal.FakeVendorFeed()
    assert [a["advisory_id"] for a in f1.advisories()] == \
           [a["advisory_id"] for a in f2.advisories()]


def test_fake_vendor_feed_filters():
    items = vendorsignal.FakeVendorFeed().advisories("air compressor")
    assert items and all(a["applies_to"] == "air compressor" for a in items)


def test_live_vendor_feed_gap():
    out = vendorsignal.LiveVendorFeed().advisories()
    assert out["gap"] is True and "reason" in out


# ---------- escalation ----------

def test_classify_tiers():
    assert escalation.classify("routine check") == "T1"
    assert escalation.classify("monitor this pump") == "T2"
    assert escalation.classify("emergency repair needed") == "T3"
    assert escalation.classify("recommend line stop", risk=0.1) == "T4"
    assert escalation.classify("all good", risk=0.9) == "T4"


def test_gate_flow():
    g = escalation.ConfirmationGate()
    token = g.request("line_stop", "stop LINE-A")
    assert g.decide(token, True) == "granted"
    token2 = g.request("emergency_work_order", "fix now")
    assert g.decide(token2, False) == "denied"


def test_gate_timeout_denies():
    g = escalation.ConfirmationGate()
    token = g.request("line_stop", "stop LINE-A")
    assert g.timeout(token) == "denied (timeout)"


def test_gate_unknown_token():
    g = escalation.ConfirmationGate()
    with pytest.raises(KeyError):
        g.decide("gate-999", True)


def test_non_gated_action_auto():
    g = escalation.ConfirmationGate()
    assert g.request("schedule_inspection", "routine") == "auto-approved"


# ---------- audit ----------

def test_audit_chain_verifies():
    log = audit.AuditLog()
    log.record("agent", "predict", {"asset": "PUMP-101"})
    log.record("user", "ack", {})
    ok, msg = log.verify_chain()
    assert ok and "2 entries verified" in msg


def test_audit_tamper_detected():
    log = audit.AuditLog()
    log.record("agent", "predict", {"asset": "PUMP-101"})
    log.entries[0]["details"]["asset"] = "HACKED"
    ok, msg = log.verify_chain()
    assert not ok and "tampered" in msg


# ---------- pii + feedback ----------

def test_pii_scrub():
    clean, n = pii.scrub("call jane@plant.test or 555-123-4567 about 123-45-6789")
    assert n == 3
    assert "[EMAIL]" in clean and "[PHONE]" in clean and "[SSN]" in clean
    assert "jane@plant.test" not in clean


def test_feedback_validates():
    log = audit.AuditLog()
    with pytest.raises(feedback.FeedbackError):
        feedback.capture_feedback(log, session_id="s", turn_id="t", rating="meh")
    with pytest.raises(feedback.FeedbackError):
        feedback.capture_feedback(log, session_id="s", turn_id="t",
                                  rating="down", correction="   ")


def test_feedback_scrubs_before_storage():
    log = audit.AuditLog()
    e = feedback.capture_feedback(log, session_id="s1", turn_id="t1",
                                  rating="down",
                                  correction="wrong asset, call bob@plant.test")
    assert e["details"]["correction"] == "wrong asset, call [EMAIL]"
    assert e["details"]["pii_redactions"] == 1
    ok, _ = log.verify_chain()
    assert ok


def test_feedback_list_filters_session():
    log = audit.AuditLog()
    feedback.capture_feedback(log, session_id="s1", turn_id="t1", rating="up")
    feedback.capture_feedback(log, session_id="s2", turn_id="t2", rating="up")
    assert len(feedback.list_feedback(log)) == 2
    assert len(feedback.list_feedback(log, session_id="s1")) == 1


# ---------- orchestrator ----------

def test_orchestrator_answer():
    conn = fresh_conn()
    orch = orchestrator.Orchestrator(conn)
    out = orch.answer("which assets are at risk of failure?")
    assert out["prediction"]["highest_risk_asset"] == "PUMP-101"
    assert out["tier"] in ("T1", "T2", "T3", "T4")
    ok, _ = orch.log.verify_chain()
    assert ok


def test_orchestrator_gates_t4():
    conn = fresh_conn()
    orch = orchestrator.Orchestrator(conn)
    out = orch.answer("recommend a line stop for LINE-B")
    assert out["tier"] == "T4"
    assert "gate_token" in out


def test_orchestrator_work_order_plan():
    conn = fresh_conn()
    orch = orchestrator.Orchestrator(conn)
    plan = orch.work_order_plan()
    assert plan["ranked"][0]["band"] == "P1"


# ---------- demo helpers ----------

def test_demo_summary():
    s = demo_helpers.reliability_summary()
    assert s["highest_risk_asset"] == "PUMP-101"
    assert s["open_work_orders"] == 4
    assert "BRG-6205" in s["parts_below_reorder"]
    assert s["worst_line"] == "LINE-B"


def test_demo_top_work_orders():
    top = demo_helpers.top_work_orders(2)
    assert len(top) == 2
    assert top[0]["score"] >= top[1]["score"]
