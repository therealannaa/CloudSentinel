"""The four ablation arms. Each consumes ArmEvents and emits an ArmResult whose
reconstructed chain is in the manifest stage schema (format parity across arms).
"""
from __future__ import annotations

import time

from benchmark.arms.base import Arm, ArmEvent, ArmResult, Candidate
from benchmark.arms import prefilter, correlate, signatures
from benchmark.arms.llm_client import get_client

_DOMAINS = ("CloudTrail", "VPC", "S3", "EC2")


def _timed(fn):
    t0 = time.perf_counter()
    out = fn()
    return out, int((time.perf_counter() - t0) * 1000)


class A4Rules(Arm):
    """A4 — prefilter + deterministic rules only, NO LLM. The key H1 baseline."""
    code = "A4"
    uses_llm = False

    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        def _do():
            kept, stats = prefilter.apply(events)
            cands = []
            for e in kept:
                ttp = signatures.detect(e.source, e.raw)
                if ttp:
                    cands.append(Candidate(e.event_id, e.source, ttp, e.event_time))
            return kept, stats, correlate.build_chain(cands), cands
        (kept, stats, chain, cands), ms = _timed(_do)
        return ArmResult("A4", chain, stats["events_in"], stats["events_out"],
                         token_cost=0, latency_ms=ms, candidates=cands)


class A2Single(Arm):
    """A2 — prefilter + single generalised LLM agent (isolates decomposition)."""
    code = "A2"
    uses_llm = True

    def __init__(self, client=None):
        self.client = client or get_client()

    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        def _do():
            kept, stats = prefilter.apply(events)
            cands, tokens = self.client.analyze(kept, role="generalist", seed=seed)
            return stats, correlate.build_chain(cands), tokens, cands
        (stats, chain, tokens, cands), ms = _timed(_do)
        return ArmResult("A2", chain, stats["events_in"], stats["events_out"],
                         token_cost=tokens, latency_ms=ms, candidates=cands)


class A3SingleRaw(Arm):
    """A3 — NO prefilter + single agent on raw logs (isolates the pre-filter)."""
    code = "A3"
    uses_llm = True

    def __init__(self, client=None):
        self.client = client or get_client()

    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        def _do():
            cands, tokens = self.client.analyze(events, role="generalist", seed=seed)
            return correlate.build_chain(cands), tokens, cands
        (chain, tokens, cands), ms = _timed(_do)
        # A3 skips the pre-filter: events_in == events_out == all events
        return ArmResult("A3", chain, len(events), len(events),
                         token_cost=tokens, latency_ms=ms, candidates=cands)


class A1Multi(Arm):
    """A1 — prefilter + 4 domain hunters + coordinator (full CloudSentinel)."""
    code = "A1"
    uses_llm = True

    def __init__(self, client=None):
        self.client = client or get_client()

    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        def _do():
            kept, stats = prefilter.apply(events)
            all_cands, tokens = [], 0
            for domain in _DOMAINS:                       # one hunter per source
                subset = [e for e in kept if e.source == domain]
                if not subset:
                    continue
                cands, tk = self.client.analyze(subset, role=domain, seed=seed)
                all_cands.extend(cands)
                tokens += tk
            return stats, correlate.build_chain(all_cands), tokens, all_cands
        (stats, chain, tokens, cands), ms = _timed(_do)
        return ArmResult("A1", chain, stats["events_in"], stats["events_out"],
                         token_cost=tokens, latency_ms=ms, candidates=cands)
