from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Finding:
    timestamp: str
    source_ip: str
    event_type: str
    severity: str
    raw_event: str
    agent_id: str
    username: str = "unknown"

    # Optional enrichment fields (added by mitre_lookup.enrich_finding)
    mitre_name: str = ""
    mitre_mitigation: str = ""
    mitre_description: str = ""

    def to_dict(self):
        d = asdict(self)
        # Strip empty enrichment fields for clean serialization
        return {k: v for k, v in d.items() if v != ""}

    @classmethod
    def from_dict(cls, data):
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    @classmethod
    def create(cls, event_type, severity, raw_event, agent_id,
               source_ip="unknown", username="unknown"):
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_ip=source_ip,
            event_type=event_type,
            severity=severity,
            raw_event=raw_event,
            agent_id=agent_id,
            username=username,
        )
