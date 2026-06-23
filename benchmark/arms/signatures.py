"""Detection signatures — the cross-domain knowledge that maps a single raw
telemetry event to a candidate ATT&CK technique.

This is the inverse of the simulator's templates, written the way a detection
engineer would: from the *observable* fields of an event (eventName / operation /
flow attributes), never from a MITRE label in the payload (there is none — the
answer-key boundary). Shared by the rules arm (A4) and the deterministic LLM
backend; a real LLM arm reasons over the same raw events instead.

Ambiguity is intentional and realistic: e.g. ListBuckets/DescribeInstances map to
T1526 (discovery) and cannot be distinguished from T1580 by signature alone, so
some discovery stages are recovered with the "wrong" (sibling) TTP — exactly the
kind of failure the benchmark is meant to expose.
"""
from __future__ import annotations

import os

EXFIL_THRESHOLD_BYTES = int(os.getenv("EXFIL_THRESHOLD_MB", "100")) * 1024 * 1024
_INTERNAL = ("10.", "172.16.", "192.168.", "169.254.")
_GPU_PREFIXES = ("p3", "p4", "g4", "g5")
_APPROVED_REGIONS = set(os.getenv("APPROVED_REGIONS", "ap-south-1").split(","))


def _is_internal(ip):
    return any(str(ip).startswith(p) for p in _INTERNAL)


def detect(source: str, raw: dict):
    """Return a ttp_id for a suspicious event, or None if it looks benign."""
    name = raw.get("eventName")
    op = raw.get("operation")

    if source == "CloudTrail":
        if name == "ConsoleLogin":
            if raw.get("result") == "Failure":
                return "T1110"
            ip = raw.get("sourceIPAddress", "")
            if ip and not _is_internal(ip):
                return "T1078.004"
            return None
        if name in ("CreateUser", "AttachUserPolicy", "PutUserPolicy"):
            return "T1098"
        if name == "CreateAccessKey":
            return "T1098.001"
        if name == "AssumeRole":
            return "T1548.005"
        if name in ("StopLogging", "DeleteTrail"):
            return "T1562.008"
        if name == "AuthorizeSecurityGroupIngress":
            return "T1190"
        if name in ("ListBuckets", "DescribeInstances"):
            # benign automation also enumerates; this is a deliberately noisy signal
            return "T1526"
        if name == "GetSecretValue":
            return "T1528"
        if name == "GetCallerIdentity" and raw.get("via") == "instance-metadata":
            return "T1552.005"
        if name == "GetBucketEncryption" and raw.get("result") == "not-configured":
            return "T1530"
        if name == "CopyObject":
            return "T1537"
        if name == "RunInstances":
            itype = str(raw.get("instanceType", ""))
            if any(itype.startswith(p) for p in _GPU_PREFIXES):
                return "T1496"
            if raw.get("region") and raw.get("region") not in _APPROVED_REGIONS:
                return "T1578"
            return "T1578"
        return None

    if source == "S3":
        if op == "GetObject":
            return "T1530"
        if op == "DeleteObject":
            return "T1485"
        if op == "CopyObject":
            return "T1537"
        return None

    if source == "VPC":
        if raw.get("action") == "REJECT":
            return "T1046"
        if int(raw.get("bytes", 0)) >= EXFIL_THRESHOLD_BYTES:
            return "T1537"
        dstport = raw.get("dstport")
        if dstport not in (None, 80, 443, 53) and int(raw.get("bytes", 0)) < 65536:
            return "T1571"
        return None

    if source == "EC2":
        if name == "RunInstances":
            itype = str(raw.get("instanceType", ""))
            if any(itype.startswith(p) for p in _GPU_PREFIXES):
                return "T1496"
            return "T1578"
        return None

    return None
