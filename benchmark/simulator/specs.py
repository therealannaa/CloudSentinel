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
    "SD-01": _s(SINGLE, "Public S3 bucket mass-read; representative of UpGuard-documented open-bucket exposures (ATT&CK T1530)", [("T1530", S3)]),
    "SD-02": _s(SINGLE, "Dangerous security-group ingress opened to 0.0.0.0/0; representative Stratus Red Team SG-misconfig pattern (Datadog) (ATT&CK T1190)", [("T1190", CT)]),
    "SD-03": _s(SINGLE, "Bulk ransom-style S3 object deletion; representative impact pattern (ATT&CK T1485)", [("T1485", S3)]),
    "SD-04": _s(SINGLE, "EC2 launch in unapproved region for cryptomining; representative pattern (ATT&CK T1578)", [("T1578", CT)]),
    "SD-05": _s(SINGLE, "IMDSv1 credential theft; TeamTNT cryptojacking worm (Cado Security 2020; Sysdig) (ATT&CK T1552.005)", [("T1552.005", CT)]),
    "SD-06": _s(SINGLE, "Network port scan against a subnet; representative active-scanning recon (ATT&CK T1046)", [("T1046", VPC)]),
    "SD-07": _s(SINGLE, "Console/API brute force; representative credential-stuffing pattern (ATT&CK T1110)", [("T1110", CT)]),
    "SD-08": _s(SINGLE, "S3 default-encryption disabled; representative misconfig-exposure pattern (ATT&CK T1530)", [("T1530", CT)]),
    "SD-09": _s(SINGLE, "CloudTrail StopLogging; defense-evasion, Stratus aws.defense-evasion.stop-cloudtrail (Datadog) (ATT&CK T1562.008)", [("T1562.008", CT)]),
    "SD-10": _s(SINGLE, "Mass IAM/resource enumeration; representative post-compromise discovery (ATT&CK T1526)", [("T1526", CT)]),
    "SD-11": _s(SINGLE, "Beaconing on a non-standard port; representative C2 pattern (ATT&CK T1571)", [("T1571", VPC)]),
    "SD-12": _s(SINGLE, "Bulk Secrets Manager access; representative secret-theft pattern (ATT&CK T1528)", [("T1528", CT)]),

    # ---- Multi-stage kill chains (15) — Atishay ----
    "KC-01": _s(MULTI, "Stolen creds -> IAM backdoor -> S3 exfil; Rhino CloudGoat IAM-privesc pattern (Rhino Security Labs)",
                [("T1078.004", CT), ("T1098.001", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-02": _s(MULTI, "SSRF -> IMDS -> discovery -> S3 exfil; Capital One breach 2019 (Krebs 2019; Appsecco analysis)",
                [("T1552.005", CT), ("T1580", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-03": _s(MULTI, "Key -> privesc -> disable logging; Rhino CloudGoat privesc + defense-evasion pattern (Rhino Security Labs)",
                [("T1078.004", CT), ("T1548.005", CT), ("T1098.001", CT), ("T1562.008", CT)]),
    "KC-04": _s(MULTI, "Cred theft -> lateral AssumeRole -> exfil; SCARLETEEL (Sysdig, Feb 2023)",
                [("T1078.004", CT), ("T1526", CT), ("T1548.005", CT), ("T1537", VPC)]),
    "KC-05": _s(MULTI, "Secrets -> discovery -> cross-account copy; representative token->cross-account exfil chain (ATT&CK T1537)",
                [("T1078.004", CT), ("T1528", CT), ("T1580", CT), ("T1537", S3)]),
    "KC-06": _s(MULTI, "New IAM user -> S3 staging -> exfil; Rhino CloudGoat IAM-persistence pattern (Rhino Security Labs)",
                [("T1098", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-07": _s(MULTI, "IMDS -> cryptomining launch -> impact; TeamTNT cryptojacking worm (Cado Security 2020; Sysdig)",
                [("T1552.005", CT), ("T1578", CT), ("T1496", EC2)]),
    "KC-08": _s(MULTI, "Brute force -> valid acct -> disable logs -> destroy; representative stuffing->destruction chain",
                [("T1110", CT), ("T1078.004", CT), ("T1562.008", CT), ("T1485", S3)]),
    "KC-09": _s(MULTI, "Phished creds -> console -> SG open -> exfil; representative phishing-for-cloud-creds chain",
                [("T1078.004", CT), ("T1190", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-10": _s(MULTI, "Public-bucket discovery -> mass download -> cross-account; representative open-bucket harvest chain",
                [("T1580", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-11": _s(MULTI, "Role chaining -> secrets -> exfil; representative AssumeRole-chaining chain (ATT&CK T1548.005)",
                [("T1548.005", CT), ("T1528", CT), ("T1537", S3)]),
    "KC-12": _s(MULTI, "Login-profile persistence -> privesc -> mining; representative persistence->hijack chain",
                [("T1098.001", CT), ("T1548.005", CT), ("T1496", EC2)]),
    "KC-13": _s(MULTI, "Lambda backdoor -> creds -> S3 exfil; representative serverless-backdoor chain",
                [("T1098", CT), ("T1528", CT), ("T1530", S3), ("T1537", VPC)]),
    "KC-14": _s(MULTI, "Snapshot/AMI exfil -> cross-account share; representative EBS-snapshot exfil (ATT&CK T1578/T1537)",
                [("T1578", CT), ("T1537", CT)]),
    "KC-15": _s(MULTI, "Slow compromise -> logging-off -> destruction; representative long-dwell destructive chain",
                [("T1078.004", CT), ("T1098.001", CT), ("T1562.008", CT), ("T1485", S3)]),

    # ---- Low-and-slow (12) — Anna ----
    "LS-01": _s(LOW, "Slow privilege escalation over days; representative long-dwell APT privesc (ATT&CK T1098)", [("T1098", CT)]),
    "LS-02": _s(LOW, "Drip-rate S3 exfiltration; representative low-and-slow exfil (ATT&CK T1530/T1537)", [("T1530", S3), ("T1537", VPC)]),
    "LS-03": _s(LOW, "Periodic beaconing C2; representative low-and-slow pattern (ATT&CK T1571)", [("T1571", VPC)]),
    "LS-04": _s(LOW, "Staged discovery across sessions; representative stealthy enumeration (ATT&CK T1526)", [("T1526", CT)]),
    "LS-05": _s(LOW, "Gradual IAM key creation across users; representative slow-persistence (ATT&CK T1098.001)", [("T1098.001", CT)]),
    "LS-06": _s(LOW, "Low-volume cross-account copy over weeks; representative stealth exfil (ATT&CK T1537)", [("T1537", S3)]),
    "LS-07": _s(LOW, "Intermittent IMDS cred-refresh abuse; representative pattern (ATT&CK T1552.005)", [("T1552.005", CT)]),
    "LS-08": _s(LOW, "Slow security-group rule drift opening ports; representative config-drift abuse (ATT&CK T1190)", [("T1190", CT)]),
    "LS-09": _s(LOW, "Sporadic brute force then success; representative slow credential-stuffing (ATT&CK T1110)", [("T1110", CT)]),
    "LS-10": _s(LOW, "Long-dwell snapshot sharing; representative snapshot exfil (ATT&CK T1578)", [("T1578", CT)]),
    "LS-11": _s(LOW, "Periodic secret access blended with legit; representative blended theft (ATT&CK T1528)", [("T1528", CT)]),
    "LS-12": _s(LOW, "Slow log-tampering (rotate off/on); representative evasion drift (ATT&CK T1562.008)", [("T1562.008", CT)]),

    # ---- Ephemeral compute (10) — Anna ----
    "EP-01": _s(EPH, "Spin-up -> mine -> terminate in minutes; representative ephemeral cryptojacking (ATT&CK T1496)", [("T1496", EC2)]),
    "EP-02": _s(EPH, "Short-lived instance for exfil staging; representative burner-exfil (ATT&CK T1537)", [("T1537", VPC)]),
    "EP-03": _s(EPH, "Transient role assume + immediate revoke; representative just-in-time abuse (ATT&CK T1548.005)", [("T1548.005", CT)]),
    "EP-04": _s(EPH, "Spot-instance cryptomining burst; representative spot-abuse (ATT&CK T1496)", [("T1496", EC2)]),
    "EP-05": _s(EPH, "Ephemeral Lambda for discovery; representative serverless recon (ATT&CK T1526)", [("T1526", CT)]),
    "EP-06": _s(EPH, "Burner instance port scan then terminate; representative recon burst (ATT&CK T1046)", [("T1046", VPC)]),
    "EP-07": _s(EPH, "Short-lived instance secrets pull; representative quick secret theft (ATT&CK T1528)", [("T1528", CT)]),
    "EP-08": _s(EPH, "Quick AMI copy then deregister; representative image exfil (ATT&CK T1578)", [("T1578", CT)]),
    "EP-09": _s(EPH, "Transient access-key create+use+delete; representative ephemeral creds (ATT&CK T1098.001)", [("T1098.001", CT)]),
    "EP-10": _s(EPH, "Ephemeral instance beacon then terminate; representative short C2 (ATT&CK T1571)", [("T1571", VPC)]),

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
    "HO-01": _s(MULTI, "Held-out novel cred-theft -> privesc -> exfil chain; representative (mirrors multi-stage)",
                [("T1078.004", CT), ("T1548.005", CT), ("T1537", VPC)], held_out=True),
    "HO-02": _s(SINGLE, "Held-out single-domain S3 abuse; representative (mirrors single-domain, ATT&CK T1530)", [("T1530", S3)], held_out=True),
    "HO-03": _s(LOW, "Held-out low-and-slow exfil variant; representative (ATT&CK T1530/T1537)",
                [("T1530", S3), ("T1537", VPC)], held_out=True),
    "HO-04": _s(EPH, "Held-out ephemeral cryptomining variant; representative (ATT&CK T1496)", [("T1496", EC2)], held_out=True),
    "HO-05": _s(BEN, "N/A - synthetic benign baseline", [], held_out=True),
    "HO-06": _s(MULTI, "Held-out multi-stage with benign decoy sub-sequence; representative (mirrors multi-stage, hard)",
                [("T1078.004", CT), ("T1098.001", CT), ("T1485", S3)], held_out=True),
    "HO-07": _s(MULTI, "Held-out novel role-chaining lateral movement; representative (mirrors multi-stage)",
                [("T1548.005", CT), ("T1526", CT), ("T1537", VPC)], held_out=True),
    "HO-08": _s(SINGLE, "Held-out single-domain logging-disable variant; representative (ATT&CK T1562.008)", [("T1562.008", CT)], held_out=True),
    "HO-09": _s(EPH, "Held-out ephemeral Lambda discovery variant; representative (ATT&CK T1526)", [("T1526", CT)], held_out=True),
    "HO-10": _s(BEN, "N/A - synthetic benign baseline", [], held_out=True),
}


def all_ids():
    return list(SCENARIO_SPECS.keys())


def dev_ids():
    return [sid for sid, spec in SCENARIO_SPECS.items() if not spec["held_out"]]


def heldout_ids():
    return [sid for sid, spec in SCENARIO_SPECS.items() if spec["held_out"]]
