"""Deterministic pre-filter (instrumented) — reduces event volume before any LLM.

Used by A1, A2, A4 (A3 skips it). Instrumentation records events-in / events-out
(the filtering ratio, contribution C3). Pre-filter *recall* — how many ground-truth
events survive — is measured by the experiment runner using is_ground_truth, never
by the filter itself (the filter must not see the answer key).
"""
from __future__ import annotations

from benchmark.arms import signatures
from benchmark.arms.base import ArmEvent

# Events that are always kept regardless of signature (high-risk control-plane ops).
_HIGH_RISK_NAMES = {
    "CreateUser", "AttachUserPolicy", "PutUserPolicy", "CreateAccessKey",
    "AssumeRole", "StopLogging", "DeleteTrail", "AuthorizeSecurityGroupIngress",
    "GetSecretValue",
}


def keep(event: ArmEvent) -> bool:
    """True if the event survives the pre-filter."""
    if event.raw.get("eventName") in _HIGH_RISK_NAMES:
        return True
    return signatures.detect(event.source, event.raw) is not None


def apply(events: list[ArmEvent]):
    """Return (kept_events, {events_in, events_out})."""
    kept = [e for e in events if keep(e)]
    return kept, {"events_in": len(events), "events_out": len(kept)}
