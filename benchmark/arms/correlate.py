"""Correlation — turn a bag of per-event Candidates into an ordered reconstructed
kill chain in the manifest stage schema.

Candidates are sorted by event time and merged: consecutive candidates sharing a
(ttp_id, telemetry_source) collapse into one stage whose evidence is the union of
their event_ids and whose timestamp_range spans them. Stage ids are assigned by
temporal order. This is the shared "coordinator" step for every arm, so all arms
emit format-parity output (docs/week1/04 Section 5).
"""
from __future__ import annotations

from benchmark.arms.base import Candidate


def build_chain(candidates: list[Candidate]) -> dict:
    if not candidates:
        return {"stages": []}

    # de-duplicate by (event_id, ttp_id) so repeated proposals don't inflate evidence
    seen = set()
    uniq = []
    for c in candidates:
        key = (c.event_id, c.ttp_id)
        if key not in seen:
            seen.add(key)
            uniq.append(c)

    uniq.sort(key=lambda c: (c.event_time, c.event_id))

    stages = []
    cur = None
    for c in uniq:
        if cur and cur["ttp_id"] == c.ttp_id and cur["telemetry_source"] == c.telemetry_source:
            cur["evidence_event_ids"].append(c.event_id)
            cur["_end"] = c.event_time
        else:
            if cur:
                stages.append(cur)
            cur = {
                "ttp_id": c.ttp_id,
                "telemetry_source": c.telemetry_source,
                "evidence_event_ids": [c.event_id],
                "_start": c.event_time,
                "_end": c.event_time,
            }
    if cur:
        stages.append(cur)

    out = []
    for i, s in enumerate(stages, start=1):
        out.append({
            "stage_id": i,
            "ttp_id": s["ttp_id"],
            "ttp_name": "",  # arms reconstruct the id; name is not scored
            "telemetry_source": s["telemetry_source"],
            "evidence_event_ids": s["evidence_event_ids"],
            "timestamp_range": [s["_start"], s["_end"]],
        })
    return {"stages": out}
