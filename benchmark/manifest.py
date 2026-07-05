"""Ground-truth manifest model + JSON-Schema validation.

Implements docs/week1/03_manifest_schema.md. The canonical machine-checkable
contract is docs/week1/manifest.schema.json; `validate()` checks any manifest
dict against it so the simulator can never emit a malformed answer key.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from functools import lru_cache

_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "week1", "manifest.schema.json",
)

CATEGORIES = (
    "single_domain", "multi_stage_kill_chain", "low_and_slow", "ephemeral", "benign",
)


@lru_cache(maxsize=1)
def _validator():
    from jsonschema import Draft202012Validator
    with open(_SCHEMA_PATH) as fh:
        schema = json.load(fh)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate(manifest_dict) -> list[str]:
    """Return a list of human-readable validation errors ([] == valid)."""
    return [e.message for e in sorted(_validator().iter_errors(manifest_dict), key=str)]


@dataclass
class Stage:
    stage_id: int
    ttp_id: str
    ttp_name: str
    telemetry_source: str
    evidence_event_ids: list[str]
    timestamp_range: list[str]  # [start, end]

    def to_dict(self):
        return asdict(self)


@dataclass
class Manifest:
    scenario_id: str
    category: str
    real_incident_reference: str
    stages: list[Stage] = field(default_factory=list)
    authorship: dict | None = None
    schema_version: str = "1.0"

    def to_dict(self):
        d = {
            "schema_version": self.schema_version,
            "scenario_id": self.scenario_id,
            "category": self.category,
            "real_incident_reference": self.real_incident_reference,
            "stages": [s.to_dict() for s in self.stages],
        }
        if self.authorship is not None:
            d["authorship"] = self.authorship
        return d

    def validate(self) -> list[str]:
        return validate(self.to_dict())

    def save(self, path):
        errors = self.validate()
        if errors:
            raise ValueError(f"manifest {self.scenario_id} invalid: {errors}")
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path

    @classmethod
    def load(cls, path):
        with open(path) as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data):
        stages = [Stage(**s) for s in data.get("stages", [])]
        return cls(
            scenario_id=data["scenario_id"],
            category=data["category"],
            real_incident_reference=data["real_incident_reference"],
            stages=stages,
            authorship=data.get("authorship"),
            schema_version=data.get("schema_version", "1.0"),
        )
