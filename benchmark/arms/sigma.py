"""Community Sigma-rules baseline (arm code SIGMA) — external baseline for docs/week1/11.

Independent of A4's team-authored `signatures.py`: this encodes a community-style
Sigma ruleset for AWS **CloudTrail + S3 data events** (modelled on the SigmaHQ
`rules/cloud/aws` catalogue). It deliberately has **no VPC/flow-log coverage** —
just like real community CloudTrail Sigma rules — so it will miss network stages
(exfil flows, port scans, beacons). Reporting that honestly is the point: it
removes the "A4 was designed to lose" objection by showing a real, independent
ruleset's profile.

No LLM, no team pre-filter: a community detector runs over the raw log stream.
Each rule maps an observable event to a single ATT&CK technique (the rule's tag).
"""
from __future__ import annotations

import time

from benchmark.arms.base import Arm, ArmEvent, ArmResult, Candidate
from benchmark.arms import correlate

_INTERNAL = ("10.", "172.16.", "192.168.", "169.254.")
_GPU_PREFIXES = ("p3", "p4", "g4", "g5")


def _internal(ip):
    return any(str(ip).startswith(p) for p in _INTERNAL)


# Human-readable catalogue of the rules (for the paper appendix / provenance).
SIGMA_RULES = [
    "aws_cloudtrail_disable_logging (StopLogging/DeleteTrail) -> T1562.008",
    "aws_iam_backdoor_users_keys (CreateAccessKey) -> T1098.001",
    "aws_iam_create_user_or_policy (CreateUser/AttachUserPolicy) -> T1098",
    "aws_sts_assumerole (AssumeRole/GetSessionToken) -> T1548.005",
    "aws_console_login_failure (ConsoleLogin Failure) -> T1110",
    "aws_console_login_new_source (ConsoleLogin Success, external IP) -> T1078.004",
    "aws_imds_credential_access (GetCallerIdentity via metadata) -> T1552.005",
    "aws_secretsmanager_retrieve (GetSecretValue) -> T1528",
    "aws_ec2_security_group_open (AuthorizeSecurityGroupIngress) -> T1190",
    "aws_enum_discovery (ListBuckets/DescribeInstances) -> T1526",
    "aws_ec2_run_instances (RunInstances; GPU type -> T1496) -> T1578",
    "aws_s3_get/delete/copy (object ops) -> T1530/T1485/T1537",
    "NOTE: no VPC/flow-log rules (CloudTrail+S3 ruleset only)",
]


def sigma_detect(source: str, raw: dict):
    """Community-ruleset detection: returns a ttp_id or None. CloudTrail + S3 only."""
    name = raw.get("eventName")
    op = raw.get("operation")

    if source in ("CloudTrail", "EC2"):
        if name in ("StopLogging", "DeleteTrail", "UpdateTrail"):
            return "T1562.008"
        if name == "CreateAccessKey":
            return "T1098.001"
        if name in ("CreateUser", "AttachUserPolicy", "PutUserPolicy", "CreateLoginProfile"):
            return "T1098"
        if name in ("AssumeRole", "GetSessionToken"):
            return "T1548.005"
        if name == "ConsoleLogin":
            if raw.get("result") == "Failure":
                return "T1110"
            ip = raw.get("sourceIPAddress", "")
            return "T1078.004" if ip and not _internal(ip) else None
        if name == "GetCallerIdentity" and raw.get("via") == "instance-metadata":
            return "T1552.005"
        if name in ("GetSecretValue", "BatchGetSecretValue"):
            return "T1528"
        if name == "AuthorizeSecurityGroupIngress":
            return "T1190"
        if name in ("ListBuckets", "DescribeInstances", "GetAccountAuthorizationDetails"):
            return "T1526"
        if name == "CopyObject":
            return "T1537"
        if name == "RunInstances":
            itype = str(raw.get("instanceType", ""))
            return "T1496" if any(itype.startswith(p) for p in _GPU_PREFIXES) else "T1578"
        return None

    if source == "S3":
        if op == "GetObject":
            return "T1530"
        if op in ("DeleteObject", "DeleteObjects"):
            return "T1485"
        if op == "CopyObject":
            return "T1537"
        return None

    # VPC / network: intentionally uncovered (CloudTrail+S3 ruleset)
    return None


class SigmaArm(Arm):
    """SIGMA baseline: community CloudTrail+S3 rules, no LLM, no team pre-filter."""
    code = "SIGMA"
    uses_llm = False

    def run(self, events: list[ArmEvent], seed: int = 0) -> ArmResult:
        t0 = time.perf_counter()
        cands = []
        for e in events:
            ttp = sigma_detect(e.source, e.raw)
            if ttp:
                cands.append(Candidate(e.event_id, e.source, ttp, e.event_time))
        chain = correlate.build_chain(cands)
        ms = int((time.perf_counter() - t0) * 1000)
        # community detector runs on the full stream (no pre-filter)
        return ArmResult("SIGMA", chain, len(events), len(events),
                         token_cost=0, latency_ms=ms, candidates=cands)
