"""Arm interfaces and the arm-visible event view."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ArmEvent:
    """The ONLY view an arm gets of an event. Deliberately excludes
    `is_ground_truth` so an arm cannot read the answer key."""
    event_id: str
    source: str
    event_time: str
    raw: dict

    @classmethod
    def from_row(cls, row):
        """Build from a sqlite Row / dict with raw_json. Ignores is_ground_truth."""
        raw = row["raw_json"]
        return cls(
            event_id=row["event_id"],
            source=row["source"],
            event_time=row["event_time"],
            raw=json.loads(raw) if isinstance(raw, str) else raw,
        )


@dataclass
class Candidate:
    """A suspicious-event detection proposed by a rule or an agent."""
    event_id: str
    telemetry_source: str
    ttp_id: str
    event_time: str
    confidence: float = 0.8


@dataclass
class ArmResult:
    arm: str
    reconstructed: dict                      # {"stages": [...]} in manifest stage schema
    prefilter_events_in: int = 0
    prefilter_events_out: int = 0
    token_cost: int = 0
    latency_ms: int = 0
    candidates: list = field(default_factory=list)

    @property
    def n_stages(self):
        return len(self.reconstructed.get("stages", []))


class Arm(ABC):
    code: str = "??"
    uses_llm: bool = False

    @abstractmethod
    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        ...
