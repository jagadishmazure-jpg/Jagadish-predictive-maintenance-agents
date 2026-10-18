"""T1-T4 escalation tiers plus human confirmation gates.

T1 informational - T2 watch - T3 action - T4 critical.
Line-stop recommendations and emergency work orders always need a
human confirmation; a gate timeout denies the action.
"""

from __future__ import annotations

TIERS = ("T1", "T2", "T3", "T4")

# PM-ESC-01: T4 triggers
LINE_STOP_KEYWORDS = ("line stop", "shutdown", "stop the line")
EMERGENCY_KEYWORDS = ("emergency", "immediate repair", "safety")


def classify(text: str, risk: float = 0.0) -> str:
    """Classify an event or recommendation into T1-T4."""
    low = text.lower()
    if any(k in low for k in LINE_STOP_KEYWORDS) or risk >= 0.8:
        return "T4"
    if any(k in low for k in EMERGENCY_KEYWORDS) or risk >= 0.5:
        return "T3"
    if risk >= 0.25 or "watch" in low or "monitor" in low:
        return "T2"
    return "T1"


class ConfirmationGate:
    """Human approval gate. grant()/deny() record a decision; timeout denies."""

    # PM-ESC-02: actions that always require confirmation
    GATED_ACTIONS = ("line_stop", "emergency_work_order")

    def __init__(self):
        self.decisions: dict[str, str] = {}

    def request(self, action: str, detail: str) -> str:
        if action not in self.GATED_ACTIONS:
            return "auto-approved"
        token = f"gate-{len(self.decisions) + 1:03d}"
        self.decisions[token] = "pending"
        return token

    def decide(self, token: str, approved: bool) -> str:
        if token not in self.decisions:
            raise KeyError(f"unknown gate token {token!r}")
        self.decisions[token] = "granted" if approved else "denied"
        return self.decisions[token]

    def timeout(self, token: str) -> str:
        """A gate timeout denies the action (fail-safe)."""
        if token in self.decisions and self.decisions[token] == "pending":
            self.decisions[token] = "denied (timeout)"
        return self.decisions.get(token, "unknown token")
