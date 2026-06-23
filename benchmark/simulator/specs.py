"""Scenario catalog — the machine-readable mirror of docs/week1/02_scenario_taxonomy.md.

Each scenario is a compact spec: category, real-incident grounding, and an ordered
list of (ttp_id, telemetry_source) stages. The generic builder (builder.py) turns
each stage into representative telemetry and a manifest stage. This keeps the
simulator in lock-step with the frozen taxonomy and covers all ~69 scenarios.

`stages` for a benign scenario is empty (ground truth = no attack).
Sources use the manifest enum: CloudTrail | VPC | S3 | EC2.
"""

CT, VPC, S3, EC2 = "CloudTrail", "VPC", "S3", "EC2"


def _s(category, incident, stages, held_out=False):
    return {"category": category, "incident": incident,
            "stages": stages, "held_out": held_out}


SINGLE = "single_domain"
MULTI = "multi_stage_kill_chain"
LOW = "low_and_slow"
EPH = "ephemeral"
BEN = "benign"

SCENARIO_SPECS = {
    # ---- Single-domain (12) — Atishay ----
    "SD-01": _s(SINGLE, "Public S3 bucket exposure (UpGuard) — VERIFY", [("T1530", S3)]),
    "SD-02": _s(SINGLE, "Stratus SG-misconfig (Datadog) — VERIFY", [("T1190", CT)]),
    "SD-03": _s(SINGLE, "Ransom-style S3 deletion — VERIFY", [("T1485", S3)]),
    "SD-04": _s(SINGLE, "Cryptomining region abuse — VERIFY", [("T1578", CT)]),
    "SD-05": _s(SINGLE, "TeamTNT IMDS theft (Cado) — VERIFY", [("T1552.005", CT)]),
    "SD-06": _s(SINGLE, "Active-scanning recon — VERIFY", [("T1046", VPC)]),
    "SD-07": _s(SINGLE, "Credential stuffing — VERIFY", [("T1110", CT)]),
    "SD-08": _s(SINGLE, "S3 encryption-disabled misconfig — VERIFY", [("T1530", CT)]),
    "SD-09": _s(SINGLE, "Defense-evasion StopLogging — VERIFY", [("T1562.008", CT)]),
    "SD-10": _s(SINGLE, "Post-compromise discovery — VERIFY", [("T1526", CT)]),
    "SD-11": _s(SINGLE, "C2 beaconing — VERIFY", [("T1571", VPC)]),
    "SD-12": _s(SINGLE, "Secret theft (bulk GetSecretValue) — VERIFY", [("T1528", CT)]),

    # ---- Multi-stage kill chains (15) — Atishay ----
    "KC-01": _s(MULTI, "Rhino/CloudGoat IAM-backdoor exfil — VERIFY",
                [("T1078.004", CT), ("T1098.001", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-02": _s(MULTI, "Capital One breach, 2019 (SSRF->IMDS->S3) — VERIFY",
                [("T1552.005", CT), ("T1580", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-03": _s(MULTI, "Rhino privesc + defense-evasion — VERIFY",
                [("T1078.004", CT), ("T1548.005", CT), ("T1098.001", CT), ("T1562.008", CT)]),
    "KC-04": _s(MULTI, "SCARLETEEL (Sysdig, 2023) — VERIFY",
                [("T1078.004", CT), ("T1526", CT), ("T1548.005", CT), ("T1537", VPC)]),
    "KC-05": _s(MULTI, "Token -> cross-account exfil — VERIFY",
                [("T1078.004", CT), ("T1528", CT), ("T1580", CT), ("T1537", S3)]),
    "KC-06": _s(MULTI, "Rhino persistence + exfil — VERIFY",
                [("T1098", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-07": _s(MULTI, "TeamTNT cryptojacking (Cado) — VERIFY",
                [("T1552.005", CT), ("T1578", CT), ("T1496", EC2)]),
    "KC-08": _s(MULTI, "Stuffing -> destructive impact — VERIFY",
                [("T1110", CT), ("T1078.004", CT), ("T1562.008", CT), ("T1485", S3)]),
    "KC-09": _s(MULTI, "Phishing-for-cloud-creds -> exfil — VERIFY",
                [("T1078.004", CT), ("T1190", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-10": _s(MULTI, "Open-bucket harvest -> cross-acct — VERIFY",
                [("T1580", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-11": _s(MULTI, "AssumeRole chaining -> secrets -> exfil — VERIFY",
                [("T1548.005", CT), ("T1528", CT), ("T1537", S3)]),
    "KC-12": _s(MULTI, "Persistence -> hijack — VERIFY",
                [("T1098.001", CT), ("T1548.005", CT), ("T1496", EC2)]),
    "KC-13": _s(MULTI, "Serverless (Lambda) backdoor exfil — VERIFY",
                [("T1098", CT), ("T1528", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-14": _s(MULTI, "EBS-snapshot/AMI cross-account exfil — VERIFY",
                [("T1578", CT), ("T1537", CT)]),
    "KC-15": _s(MULTI, "Long-dwell destructive compromise — VERIFY",
                [("T1078.004", CT), ("T1098.001", CT), ("T1562.008", CT), ("T1485", S3)]),

    # ---- Low-and-slow (12) — Anna ----
    "LS-01": _s(LOW, "Long-dwell APT privesc — VERIFY", [("T1098", CT)]),
    "LS-02": _s(LOW, "Low-and-slow exfil — VERIFY", [("T1530", S3), ("T1537", VPC)]),
    "LS-03": _s(LOW, "Beaconing C2 — VERIFY", [("T1571", VPC)]),
    "LS-04": _s(LOW, "Stealthy enumeration — VERIFY", [("T1526", CT)]),
    "LS-05": _s(LOW, "Slow persistence (key creation) — VERIFY", [("T1098.001", CT)]),
    "LS-06": _s(LOW, "Stealth cross-account copy — VERIFY", [("T1537", S3)]),
    "LS-07": _s(LOW, "Cred reuse (IMDS refresh) — VERIFY", [("T1552.005", CT)]),
    "LS-08": _s(LOW, "SG config-drift abuse — VERIFY", [("T1190", CT)]),
    "LS-09": _s(LOW, "Slow credential stuffing — VERIFY", [("T1110", CT)]),
    "LS-10": _s(LOW, "Snapshot exfil (long-dwell) — VERIFY", [("T1578", CT)]),
    "LS-11": _s(LOW, "Blended secret theft — VERIFY", [("T1528", CT)]),
    "LS-12": _s(LOW, "Evasion drift (log off/on) — VERIFY", [("T1562.008", CT)]),

    # ---- Ephemeral compute (10) — Anna ----
    "EP-01": _s(EPH, "Ephemeral cryptojacking — VERIFY", [("T1496", EC2)]),
    "EP-02": _s(EPH, "Burner exfil instance — VERIFY", [("T1537", VPC)]),
    "EP-03": _s(EPH, "Just-in-time role abuse — VERIFY", [("T1548.005", CT)]),
    "EP-04": _s(EPH, "Spot-instance mining burst — VERIFY", [("T1496", EC2)]),
    "EP-05": _s(EPH, "Serverless recon (Lambda) — VERIFY", [("T1526", CT)]),
    "EP-06": _s(EPH, "Recon burst then terminate — VERIFY", [("T1046", VPC)]),
    "EP-07": _s(EPH, "Quick secret theft — VERIFY", [("T1528", CT)]),
    "EP-08": _s(EPH, "Image exfil (AMI copy) — VERIFY", [("T1578", CT)]),
    "EP-09": _s(EPH, "Ephemeral creds — VERIFY", [("T1098.001", CT)]),
    "EP-10": _s(EPH, "Short C2 beacon — VERIFY", [("T1571", VPC)]),

    # ---- Benign noise (10) — Anna — ground truth = no attack ----
    "BN-01": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-02": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-03": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-04": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-05": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-06": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-07": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-08": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-09": _s(BEN, "N/A - synthetic benign baseline", []),
    "BN-10": _s(BEN, "N/A - synthetic benign baseline", []),

    # ---- Held-out (10) — Anna — sealed in P2 ----
    "HO-01": _s(MULTI, "Held-out novel cred-theft chain — VERIFY",
                [("T1078.004", CT), ("T1548.005", CT), ("T1537", VPC)], held_out=True),
    "HO-02": _s(SINGLE, "Held-out S3 abuse — VERIFY", [("T1530", S3)], held_out=True),
    "HO-03": _s(LOW, "Held-out low-and-slow exfil — VERIFY",
                [("T1530", S3), ("T1537", VPC)], held_out=True),
    "HO-04": _s(EPH, "Held-out cryptomining — VERIFY", [("T1496", EC2)], held_out=True),
    "HO-05": _s(BEN, "N/A - synthetic benign baseline", [], held_out=True),
    "HO-06": _s(MULTI, "Held-out multi-stage with decoy — VERIFY",
                [("T1078.004", CT), ("T1098.001", CT), ("T1485", S3)], held_out=True),
    "HO-07": _s(MULTI, "Held-out role-chaining lateral — VERIFY",
                [("T1548.005", CT), ("T1526", CT), ("T1537", VPC)], held_out=True),
    "HO-08": _s(SINGLE, "Held-out logging-disable — VERIFY", [("T1562.008", CT)], held_out=True),
    "HO-09": _s(EPH, "Held-out Lambda discovery — VERIFY", [("T1526", CT)], held_out=True),
    "HO-10": _s(BEN, "N/A - synthetic benign baseline", [], held_out=True),
}


def all_ids():
    return list(SCENARIO_SPECS.keys())


def dev_ids():
    return [sid for sid, spec in SCENARIO_SPECS.items() if not spec["held_out"]]


def heldout_ids():
    return [sid for sid, spec in SCENARIO_SPECS.items() if spec["held_out"]]
