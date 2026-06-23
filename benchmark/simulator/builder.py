"""Generic scenario builder: turns a compact spec (specs.py) into deterministic
telemetry (Event list) + a ground-truth Manifest.

The synthetic backend produces representative telemetry per ATT&CK technique via
TTP_TEMPLATES, with deterministic timestamps seeded by scenario_id, plus a small
amount of benign "noise" so the matching function's evidence-binding and FP
accounting are exercised. The emitted event + manifest schema is identical to
what the LocalStack backend would capture.

Answer-key boundary: ground-truth events are NOT labelled in their payload. Their
raw_json is indistinguishable from benign noise (just as a real attack API call is
indistinguishable from a normal one in isolation — recovering the chain is the whole
challenge). Ground truth lives only in the Event.is_ground_truth flag and the
manifest's evidence_event_ids. When the arms are built (P3) they must read only the
arm-visible columns (event_id, source, event_time, raw_json) from the events table
and never the is_ground_truth column.
"""
from __future__ import annotations

import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from benchmark.events import Event
from benchmark.manifest import Manifest, Stage
from tools.mitre_lookup import CLOUD_TECHNIQUES

# Sub-techniques referenced in the taxonomy but not yet in tools/mitre_lookup.py
# (docs/week1/02 Section 3 "to-add"). Names kept here until added to the curated set.
EXTRA_TTP_NAMES = {
    "T1098.001": "Account Manipulation: Additional Cloud Credentials",
    "T1548.005": "Abuse Elevation Control Mechanism: Temporary Elevated Cloud Access",
    "T1562.008": "Impair Defenses: Disable Cloud Logs",
}

# Base time for the synthetic clock. Deterministic per scenario.
_BASE = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

# Inter-stage gap (seconds) — wide for low-and-slow to exercise temporal handling.
_GAP = {"low_and_slow": 6 * 3600, "ephemeral": 20}
_DEFAULT_GAP = 60


def ttp_name(ttp_id: str) -> str:
    if ttp_id in CLOUD_TECHNIQUES:
        return CLOUD_TECHNIQUES[ttp_id]["name"]
    return EXTRA_TTP_NAMES.get(ttp_id, ttp_id)


# --- per-TTP telemetry templates -----------------------------------------------
# Each returns a list of raw-event dicts representing that stage. `n` controls
# multiplicity (e.g. mass download / port scan emit several events).

def _ct(event_name, **kw):
    # `ttp=` is accepted at call sites for readability (it documents which technique
    # the stage represents) but is deliberately NOT written into the event payload:
    # real CloudTrail/VPC/S3 telemetry carries no MITRE label, and emitting one would
    # leak the answer key to the arms. Ground truth lives in `is_ground_truth` + the
    # manifest's evidence_event_ids, never in raw_json.
    kw.pop("ttp", None)
    return {"eventName": event_name, **kw}


def _events_for(ttp_id, source):
    """Return a list of raw-event dicts for one stage of (ttp_id, source)."""
    t = ttp_id
    if t == "T1078.004":
        return [_ct("ConsoleLogin", ttp=t, userIdentity="compromised-user",
                    sourceIPAddress="203.0.113.5", result="Success")]
    if t in ("T1098", ):
        return [_ct("CreateUser", ttp=t, userName="backdoor"),
                _ct("AttachUserPolicy", ttp=t, policyArn="arn:aws:iam::aws:policy/AdministratorAccess")]
    if t == "T1098.001":
        return [_ct("CreateAccessKey", ttp=t, targetUser="victim-user")]
    if t in ("T1548", "T1548.005"):
        return [_ct("AssumeRole", ttp=t, roleArn="arn:aws:iam::role/elevated")]
    if t == "T1562.008":
        return [_ct("StopLogging", ttp=t, trailName="org-trail")]
    if t == "T1110":
        return [_ct("ConsoleLogin", ttp=t, result="Failure",
                    sourceIPAddress="203.0.113.5") for _ in range(6)]
    if t == "T1190":
        return [_ct("AuthorizeSecurityGroupIngress", ttp=t, port=22, cidr="0.0.0.0/0")]
    if t in ("T1526", "T1580"):
        return [_ct("ListBuckets", ttp=t), _ct("DescribeInstances", ttp=t)]
    if t == "T1528":
        return [_ct("GetSecretValue", ttp=t, secretId="prod/db/password")]
    if t == "T1552.005":
        return [_ct("GetCallerIdentity", ttp=t, via="instance-metadata",
                    sourceIPAddress="169.254.169.254")]
    if t == "T1578":
        return [_ct("RunInstances", ttp=t, region="us-west-2", instanceType="c5.large")]
    if t == "T1485":
        return [{"operation": "DeleteObject", "bucket": "prod-data",
                 "key": f"obj-{i}"} for i in range(8)]
    if t == "T1530":
        if source == "S3":
            return [{"operation": "GetObject", "bucket": "prod-data",
                     "key": f"obj-{i}", "http_status": 200}
                    for i in range(6)]
        return [_ct("GetBucketEncryption", ttp=t, bucket="prod-data", result="not-configured")]
    if t == "T1537":
        if source == "VPC":
            return [{"srcaddr": "10.0.0.7", "dstaddr": "198.51.100.9", "dstport": 443,
                     "protocol": "tcp", "action": "ACCEPT", "bytes": 250_000_000,
                     "packets": 180_000}]
        return [{"operation": "CopyObject", "bucket": "attacker-acct-bucket",
                 "key": "exfil.tar"}]
    if t == "T1046":
        return [{"srcaddr": "203.0.113.5", "dstaddr": "10.0.0.20", "dstport": p,
                 "protocol": "tcp", "action": "REJECT", "bytes": 0}
                for p in range(20, 45)]
    if t == "T1571":
        return [{"srcaddr": "10.0.0.7", "dstaddr": "198.51.100.9", "dstport": 4444,
                 "protocol": "tcp", "action": "ACCEPT", "bytes": 1024} for _ in range(4)]
    if t == "T1496":
        return [{"eventName": "RunInstances", "instanceType": "p3.2xlarge",
                 "state": "running"}]
    # generic fallback: one event on the declared source
    return [{"eventName": "GenericEvent", "source": source}]


# benign noise: not tied to any stage; never ground truth.
def _benign_noise(scenario_id, start, n=4):
    raws = [
        ("CloudTrail", _ct("ConsoleLogin", result="Success", userIdentity="alice", sourceIPAddress="10.0.0.2")),
        ("S3", {"operation": "GetObject", "bucket": "app-assets", "key": "logo.png", "http_status": 200}),
        ("CloudTrail", _ct("DescribeInstances", userIdentity="ops")),
        ("EC2", {"eventName": "DescribeVolumes", "userIdentity": "ops"}),
        ("CloudTrail", _ct("ListBuckets", userIdentity="backup-job")),
        ("VPC", {"srcaddr": "10.0.0.3", "dstaddr": "10.0.0.9", "dstport": 443,
                 "protocol": "tcp", "action": "ACCEPT", "bytes": 5000}),
    ]
    events = []
    for i in range(n):
        source, raw = raws[i % len(raws)]
        ts = (start + timedelta(seconds=7 * i)).isoformat()
        events.append(Event.create(scenario_id, 0, i, source, ts, raw, is_ground_truth=False))
    return events


def build_scenario(scenario_id, spec, author="Atishay", reviewer=None):
    """Return (events, Manifest) for one scenario."""
    category = spec["category"]
    gap = _GAP.get(category, _DEFAULT_GAP)
    clock = _BASE
    events: list[Event] = []
    stages: list[Stage] = []

    for idx, (ttp_id, source) in enumerate(spec["stages"], start=1):
        raws = _events_for(ttp_id, source)
        stage_events = []
        for j, raw in enumerate(raws):
            ts = (clock + timedelta(seconds=j)).isoformat()
            ev = Event.create(scenario_id, idx, j, source, ts, raw, is_ground_truth=True)
            stage_events.append(ev)
        events.extend(stage_events)
        t_start = stage_events[0].event_time
        t_end = stage_events[-1].event_time
        stages.append(Stage(
            stage_id=idx,
            ttp_id=ttp_id,
            ttp_name=ttp_name(ttp_id),
            telemetry_source=source,
            evidence_event_ids=[e.event_id for e in stage_events],
            timestamp_range=[t_start, t_end],
        ))
        clock += timedelta(seconds=gap)

    # benign noise interleaved (more for benign-only scenarios)
    noise_n = 6 if category == "benign" else 4
    events.extend(_benign_noise(scenario_id, _BASE, n=noise_n))

    authorship = {
        "author": author,
        "reviewer": reviewer or "",
        "review_date": "TBD",
        "authored_before_system_final": True,
    }
    manifest = Manifest(
        scenario_id=scenario_id,
        category=category,
        real_incident_reference=spec["incident"],
        stages=stages,
        authorship=authorship,
    )
    return events, manifest
