# Scenario Taxonomy — CloudKC-Bench

**Owners:** Atishay (single-domain `SD-*` + multi-stage `KC-*`) · Anna (low-and-slow `LS-*`, ephemeral
`EP-*`, benign `BN-*`, held-out `HO-*`)
**Status:** DRAFT catalog for Week-1 freeze. Exact per-event signatures are filled in Week 2 once the
`attack_simulator` produces real logs; Week 1 fixes the *set*, the *categories*, the *TTP grounding*, and the
*stage structure*.

> **Why this document exists (plain language).** A "scenario" is a scripted attack we will later replay in
> LocalStack to generate logs. This file is the master list of every scenario, what attacker technique each
> one exercises (its ATT&CK TTP ID), and which real-world incident it is based on. Pinning this list **now**,
> before any code, is what lets us later claim the benchmark is realistic and not cherry-picked.

---

## 1. The five categories (never pooled in analysis)

| Code | Category | Count | Why it exists |
|------|----------|-------|---------------|
| `SD` | Single-domain attacks | 6 | Sanity floor — should be caught even by simple rules (A4). |
| `KC` | Multi-stage kill chains | 8 | **Primary test of cross-domain correlation (H1).** |
| `LS` | Low-and-slow evasion | 4 | Tests temporal correlation across long time windows. |
| `EP` | Ephemeral compute | 3 | Tests SQLite state-capture of short-lived resources. |
| `BN` | Benign noise | 3 | FPR measurement; ground truth = **no attack** (empty `stages`). |
| | **Dev-set total** | **24** | |
| `HO` | Held-out validation | 4–6 | Sealed before P3; eliminates selection bias. |

> **Discrepancy flagged for the supervisor sync (`07`):** the implementation plan lists Atishay authoring
> **6** multi-stage scenarios (→ 22 dev total), while the study guide §4.2 lists **8** multi-stage (→ 24 dev
> total). **This catalog defaults to 8 (`KC-01`…`KC-08`) for a 24-scenario dev set.** Confirm at sync.

## 2. TTP grounding & a note on the technique set

TTP IDs below are grounded in the 19 techniques curated in `tools/mitre_lookup.py` wherever possible. Three
sub-techniques used here are **not yet in that table** and should be added in Week 2:

| Used here | Status | Note |
|-----------|--------|------|
| `T1098.001` Account Manipulation: Additional Cloud Credentials | add | repo has parent `T1098` |
| `T1548.005` Abuse Elevation Control: Temporary Elevated Cloud Access | add | repo has parent `T1548` |
| `T1562.008` Impair Defenses: Disable Cloud Logs | add | repo has `T1562.001`; **`.008` is the correct cloud-log-disabling sub-technique** |

> **Citation rule (from the spec's verification ledger).** Every `real_incident_reference` below is a
> *grounding pointer* and **must be confirmed to a locatable source** (URL / report / CVE) at lock time. They
> are recognisable public incidents/research; verify the exact source before the pre-registration is signed.

---

## 3. Master catalog

### 3.1 Single-domain attacks (`SD-*`) — Owner: Atishay
Each touches **one** telemetry source; one or two TTPs; the A4 rules arm should catch these.

| ID | Title | TTP ID(s) | Telemetry | Real-incident grounding |
|----|-------|-----------|-----------|--------------------------|
| SD-01 | Public S3 bucket / mass object read | T1530 | S3 | Numerous public S3 exposures (e.g. UpGuard-documented open buckets) |
| SD-02 | Dangerous security-group port opened (22/3389) | T1190 | CloudTrail | Stratus `aws.exfiltration`/SG-misconfig technique catalog (Datadog) |
| SD-03 | Bulk S3 object deletion (data destruction) | T1485 | S3 / CloudTrail | Ransom-style S3 deletion incidents |
| SD-04 | EC2 launch in unapproved region | T1578 | CloudTrail / EC2 | Cryptomining region-abuse patterns |
| SD-05 | IMDSv1 credential access (SSRF-style) | T1552.005 | CloudTrail / EC2 | TeamTNT IMDS credential theft (Cado/Trend Micro) |
| SD-06 | Network port scan against subnet | T1046 / T1595 | VPC Flow / Zeek | Generic active-scanning recon (Zeek notice) |

### 3.2 Multi-stage kill chains (`KC-*`) — Owner: Atishay
Each chain exercises **≥ 3 connected stages across ≥ 2 telemetry sources** (per study guide §1.3). Stage
outlines are in §4.

| ID | Title | Stage TTPs (ordered) | Telemetry touched | Real-incident grounding |
|----|-------|----------------------|-------------------|--------------------------|
| KC-01 | Stolen creds → IAM backdoor → S3 exfil | T1078.004 → T1098.001 → T1530 → T1537 | CloudTrail, S3, VPC | Rhino Security Labs AWS privesc / CloudGoat |
| KC-02 | SSRF → IMDS creds → discovery → S3 exfil | T1552.005 → T1580 → T1530 → T1537 | CloudTrail, EC2, S3, VPC | **Capital One 2019** (SSRF→IMDS→S3) |
| KC-03 | Compromised key → privesc → disable logging | T1078.004 → T1548.005 → T1098.001 → T1562.008 | CloudTrail | Rhino privesc + defense-evasion |
| KC-04 | Cloud cred theft → lateral AssumeRole → exfil | T1078.004 → T1526 → T1548.005 → T1537 | CloudTrail, VPC | **SCARLETEEL** (Sysdig, 2023) |
| KC-05 | Secrets access → discovery → cross-account copy | T1078.004 → T1528 → T1580 → T1537 | CloudTrail, S3 | Token-theft → cross-account exfil patterns |
| KC-06 | Persistence via new IAM user → S3 staging → exfil | T1098 → T1530 → T1537 | CloudTrail, S3, VPC | Rhino persistence + exfil |
| KC-07 | IMDS creds → cryptomining launch → impact | T1552.005 → T1578 → T1496 | CloudTrail, EC2 | TeamTNT cryptojacking (Cado) |
| KC-08 | Brute force → valid account → disable logs → destroy | T1110 → T1078.004 → T1562.008 → T1485 | CloudTrail, S3 | Credential-stuffing → destructive impact |

### 3.3 Low-and-slow evasion (`LS-*`) — Owner: Anna
Attacks deliberately spread over long windows to defeat naive temporal correlation.

| ID | Title | TTP ID(s) | Telemetry | Real-incident grounding |
|----|-------|-----------|-----------|--------------------------|
| LS-01 | Slow privilege escalation over days | T1098 / T1548.005 | CloudTrail | Long-dwell APT cloud privesc |
| LS-02 | Drip-rate S3 exfiltration (small objects, long gaps) | T1530 / T1537 | S3 / VPC | Low-and-slow exfil tradecraft |
| LS-03 | Periodic beaconing / C2 on non-standard port | T1571 | VPC Flow / Zeek | Beaconing C2 patterns |
| LS-04 | Staged discovery spread across many sessions | T1526 / T1580 | CloudTrail | Stealthy enumeration |

### 3.4 Ephemeral compute (`EP-*`) — Owner: Anna
Short-lived resources that must be captured before they disappear (tests SQLite state-capture; see
`EPHEMERAL_INSTANCE_THRESHOLD` in `config.py`).

| ID | Title | TTP ID(s) | Telemetry | Real-incident grounding |
|----|-------|-----------|-----------|--------------------------|
| EP-01 | Spin-up → mine → terminate within minutes | T1496 / T1578 | EC2 / CloudTrail | Ephemeral cryptojacking |
| EP-02 | Short-lived instance used for exfil staging | T1537 | EC2 / VPC / S3 | Burner-instance exfil |
| EP-03 | Transient role assumption + immediate revoke | T1548.005 | CloudTrail | Just-in-time abuse |

### 3.5 Benign noise (`BN-*`) — Owner: Anna
**Ground truth = no attack.** Manifest has an empty `stages` array. These measure FPR.

| ID | Title | TTP ID(s) | Telemetry | Notes |
|----|-------|-----------|-----------|-------|
| BN-01 | Normal admin day (legit IAM + S3 + EC2 activity) | — | all | Should produce **zero** detected stages |
| BN-02 | Legit bulk data migration (large S3 + transfer) | — | S3 / VPC | Looks like exfil but is authorised |
| BN-03 | Scheduled autoscaling churn (instances up/down) | — | EC2 | Looks ephemeral but is benign |

### 3.6 Held-out validation (`HO-*`) — Owner: Anna — **SEAL IN WEEK 2**
Authored now, but **moved to a sealed directory in Week 2 and not run against the system until P4 is
complete** (selection-bias fix, spec §9.6 / study guide §4.3). Any scenario used during development — even
once — is contaminated and may not be held-out.

| ID | Title | TTP ID(s) | Telemetry | Mirrors category |
|----|-------|-----------|-----------|------------------|
| HO-01 | Novel cred-theft → privesc → exfil chain | T1078.004 → T1548.005 → T1537 | CloudTrail, S3, VPC | multi-stage |
| HO-02 | Unseen single-domain S3 abuse | T1530 | S3 | single-domain |
| HO-03 | Low-and-slow exfil variant | T1530 / T1537 | S3 / VPC | low-and-slow |
| HO-04 | Ephemeral cryptomining variant | T1496 | EC2 | ephemeral |
| HO-05 | Benign-but-noisy ops day | — | all | benign |
| HO-06 | Multi-stage with a decoy benign sub-sequence | T1078.004 → T1098.001 → T1485 | CloudTrail, S3 | multi-stage (hard) |

---

## 4. Stage outlines for the multi-stage chains (`KC-*`)

Format per stage: `stage_id`. tactic — `TTP` — expected log source.

**KC-01 — Stolen creds → IAM backdoor → S3 exfil**
1. Initial Access — `T1078.004` (valid cloud account, new IP) — CloudTrail
2. Persistence/PrivEsc — `T1098.001` (CreateAccessKey on another user) — CloudTrail
3. Collection — `T1530` (mass GetObject) — S3
4. Exfiltration — `T1537` (large outbound transfer) — VPC Flow

**KC-02 — SSRF → IMDS creds → discovery → S3 exfil** *(Capital One pattern)*
1. Credential Access — `T1552.005` (IMDS credential theft) — CloudTrail/EC2
2. Discovery — `T1580` (DescribeInstances/ListBuckets) — CloudTrail
3. Collection — `T1530` (mass GetObject) — S3
4. Exfiltration — `T1537` (large outbound) — VPC Flow

**KC-03 — Compromised key → privesc → disable logging**
1. Initial Access — `T1078.004` — CloudTrail
2. Privilege Escalation — `T1548.005` (AssumeRole with unexpected perms) — CloudTrail
3. Persistence — `T1098.001` (add credentials) — CloudTrail
4. Defense Evasion — `T1562.008` (StopLogging/DeleteTrail) — CloudTrail

**KC-04 — Cloud cred theft → lateral AssumeRole → exfil** *(SCARLETEEL pattern)*
1. Initial Access — `T1078.004` — CloudTrail
2. Discovery — `T1526` (cloud service discovery) — CloudTrail
3. Lateral Movement — `T1548.005` (AssumeRole) — CloudTrail + VPC
4. Exfiltration — `T1537` — VPC Flow

**KC-05 — Secrets access → discovery → cross-account copy**
1. Initial Access — `T1078.004` — CloudTrail
2. Credential Access — `T1528` (GetSecretValue) — CloudTrail
3. Discovery — `T1580` — CloudTrail
4. Exfiltration — `T1537` (cross-account CopyObject) — S3/CloudTrail

**KC-06 — Persistence via new IAM user → S3 staging → exfil**
1. Persistence — `T1098` (CreateUser/AttachUserPolicy) — CloudTrail
2. Collection — `T1530` (stage objects) — S3
3. Exfiltration — `T1537` — VPC Flow

**KC-07 — IMDS creds → cryptomining launch → impact**
1. Credential Access — `T1552.005` — CloudTrail/EC2
2. Defense Evasion / Infra mod — `T1578` (launch in odd region / large instance) — CloudTrail/EC2
3. Impact — `T1496` (resource hijacking / cryptomining) — EC2/CloudWatch

**KC-08 — Brute force → valid account → disable logs → destroy**
1. Credential Access — `T1110` (brute force) — CloudTrail
2. Initial Access — `T1078.004` — CloudTrail
3. Defense Evasion — `T1562.008` (StopLogging) — CloudTrail
4. Impact — `T1485` (bulk delete) — S3/CloudTrail

---

## 5. Worked manifest examples

These conform to `03_manifest_schema.md` / `manifest.schema.json`. `evidence_event_ids` are **placeholders**;
real IDs are bound in Week 2 when logs exist. (These three examples are validated against the JSON Schema as
part of Week-1 verification.)

### 5.1 Single-domain example — `SD-01`
```json
{
  "scenario_id": "SD-01",
  "category": "single_domain",
  "real_incident_reference": "Public S3 bucket exposure (UpGuard-documented open buckets) — VERIFY URL at lock",
  "stages": [
    {
      "stage_id": 1,
      "ttp_id": "T1530",
      "ttp_name": "Data from Cloud Storage Object",
      "telemetry_source": "S3",
      "evidence_event_ids": ["s3-0001", "s3-0002", "s3-0003"],
      "timestamp_range": ["T+0s", "T+45s"]
    }
  ]
}
```

### 5.2 Multi-stage example — `KC-02` (Capital One pattern)
```json
{
  "scenario_id": "KC-02",
  "category": "multi_stage_kill_chain",
  "real_incident_reference": "Capital One breach, 2019 (SSRF -> IMDS -> S3 exfiltration) — VERIFY source at lock",
  "stages": [
    {
      "stage_id": 1,
      "ttp_id": "T1552.005",
      "ttp_name": "Unsecured Credentials: Cloud Instance Metadata API",
      "telemetry_source": "CloudTrail",
      "evidence_event_ids": ["ct-1001"],
      "timestamp_range": ["T+0s", "T+20s"]
    },
    {
      "stage_id": 2,
      "ttp_id": "T1580",
      "ttp_name": "Cloud Infrastructure Discovery",
      "telemetry_source": "CloudTrail",
      "evidence_event_ids": ["ct-1015", "ct-1016"],
      "timestamp_range": ["T+25s", "T+60s"]
    },
    {
      "stage_id": 3,
      "ttp_id": "T1530",
      "ttp_name": "Data from Cloud Storage Object",
      "telemetry_source": "S3",
      "evidence_event_ids": ["s3-2001", "s3-2002", "s3-2003"],
      "timestamp_range": ["T+65s", "T+140s"]
    },
    {
      "stage_id": 4,
      "ttp_id": "T1537",
      "ttp_name": "Transfer Data to Cloud Account",
      "telemetry_source": "VPC",
      "evidence_event_ids": ["vpc-3001"],
      "timestamp_range": ["T+140s", "T+180s"]
    }
  ]
}
```

### 5.3 Benign example — `BN-01` (ground truth = no attack)
```json
{
  "scenario_id": "BN-01",
  "category": "benign",
  "real_incident_reference": "N/A - synthetic benign baseline",
  "stages": []
}
```
