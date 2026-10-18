"""Jagadish-predictive-maintenance-agents: end-to-end manufacturing asset reliability.

Synthetic telemetry, text-to-SQL over read-only views, SOP RAG,
failure-prediction scorer, work-order prioritizer, escalation tiers,
hash-chained audit.
All data is fictional and generated deterministically (seed 42).
"""

from . import (
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

__all__ = [
    "audit",
    "demo_helpers",
    "escalation",
    "feedback",
    "orchestrator",
    "pii",
    "predict",
    "prioritize",
    "sop_rag",
    "telemetry",
    "text2sql",
    "vendorsignal",
    "views",
]
