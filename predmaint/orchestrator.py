"""ReAct orchestrator: plan, fan out across tools, classify, audit.

One turn: detect intents in the question, run matching tools, attach
prediction scores where relevant, classify the tier, and record everything
to the audit chain.
"""

from __future__ import annotations

import sqlite3

from . import audit, escalation, predict, prioritize, sop_rag, text2sql, vendorsignal


class Orchestrator:
    def __init__(self, conn: sqlite3.Connection, vendor=None):
        self.conn = conn
        self.log = audit.AuditLog()
        self.gate = escalation.ConfirmationGate()
        self.vendor = vendor or vendorsignal.FakeVendorFeed()

    def answer(self, question: str, session_id: str = "demo") -> dict:
        self.log.record("user", "question", {"text": question, "session": session_id})
        result: dict = {"question": question}
        try:
            tq = text2sql.run_question(self.conn, question)
            result["sql"] = tq
            self.log.record("agent", "text2sql", {"intent": tq["intent"],
                                                  "rows": tq["row_count"]})
        except text2sql.EscalationNeeded as exc:
            result["sql"] = {"escalated": str(exc)}
            self.log.record("agent", "escalation", {"reason": str(exc)})

        rag = sop_rag.retrieve(question)
        result["sop"] = rag

        scored = predict.predict_all(self.conn)
        worst = scored[0]
        result["prediction"] = {
            "highest_risk_asset": worst["asset_id"],
            "risk": worst["risk"],
            "rul_days": worst["rul_days"],
        }
        tier = escalation.classify(question, risk=worst["risk"])
        result["tier"] = tier
        self.log.record("agent", "tier", {"tier": tier})

        if tier in ("T3", "T4"):
            token = self.gate.request("line_stop", f"tier {tier}: {question[:60]}")
            result["gate_token"] = token
        return result

    def work_order_plan(self) -> dict:
        ranked = prioritize.prioritize(self.conn)
        self.log.record("agent", "prioritize", {"n": len(ranked)})
        return {"ranked": ranked}
