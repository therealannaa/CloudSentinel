"""Normalized telemetry event — the shared schema collectors/simulator emit.

One Event corresponds to one row in the `events` table (docs/week1/05). The
`event_id` is the stable identifier referenced by a manifest stage's
`evidence_event_ids` (docs/week1/03), which is what lets the matching function's
evidence-binding check work (docs/week1/04 Section 2.2).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict

# Telemetry sources — must match the manifest schema `telemetry_source` enum.
SOURCES = ("CloudTrail", "VPC", "S3", "EC2")


@dataclass
class Event:
    event_id: str                 # e.g. "KC-02-s1-0"; used in manifest evidence_event_ids
    scenario_id: str
    source: str                   # one of SOURCES
    event_time: str               # ISO-8601 UTC
    raw_json: str                 # original event payload (JSON string)
    normalized: dict = field(default_factory=dict)  # normalized fields (shared)
    is_ground_truth: bool = False  # True if this event belongs to a manifest stage
    pre_filter_passed: bool = False  # set by the deterministic pre-filter (P3)
    environment: str = "synthetic"   # synthetic | localstack | real_aws

    def __post_init__(self):
        if self.source not in SOURCES:
            raise ValueError(f"unknown telemetry source: {self.source!r}")

    @classmethod
    def create(cls, scenario_id, stage_id, index, source, event_time,
               raw, is_ground_truth=False, normalized=None, environment="synthetic"):
        """Build an Event with a deterministic id of the form
        ``<scenario>-s<stage>-<index>`` (stage 0 = benign noise)."""
        eid = f"{scenario_id}-s{stage_id}-{index}"
        return cls(
            event_id=eid,
            scenario_id=scenario_id,
            source=source,
            event_time=event_time,
            raw_json=json.dumps(raw, default=str, sort_keys=True),
            normalized=normalized or {},
            is_ground_truth=is_ground_truth,
            environment=environment,
        )

    def to_row(self):
        """Tuple matching the `events` table column order in state_cache."""
        return (
            self.event_id, self.scenario_id, self.environment, self.source,
            self.event_time, self.raw_json, json.dumps(self.normalized, default=str),
            int(self.pre_filter_passed), int(self.is_ground_truth),
        )

    def to_dict(self):
        d = asdict(self)
        return d
