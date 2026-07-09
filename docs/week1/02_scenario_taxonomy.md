# Scenario Taxonomy — CloudKC-Bench (Journal-Tier, ~70 Scenarios)

**Owners:** Atishay (`SD-*` + `KC-*`) · Anna (`LS-*`, `EP-*`, `BN-*`, `HO-*`)
**Status:** DRAFT catalog for P1 freeze. Per-event signatures are bound in P2 once the `attack_simulator`
produces real logs; P1 fixes the *set*, *categories*, *TTP grounding*, and *stage structure*.

> **v3 (journal) — changed from v2:** scenario count raised 24 → **~70** for per-category statistical power
> after Holm-Bonferroni (see `08_power_analysis.md`). Counts: 12 SD / 15 KC / 12 LS / 10 EP / 10 BN (= 59 dev)
> + 10 held-out (~70 total). Added an **inter-rater review** requirement (≥20% independently reviewed) and an
> explicit **held-out authorship-separation** statement (v3 §4.3). The old v2 "6-vs-8 multi-stage" question is
> resolved: **15 KC**.

> **Why this document exists (plain language).** A "scenario" is a scripted attack we replay in
> LocalStack (and later real AWS) to generate logs. This file is the master list: what attacker technique each
> exercises (ATT&CK TTP ID) and which real incident it is based on. Pinning it now, before code, is what lets
> us later defend that the benchmark is realistic and not cherry-picked.

---

## 1. The five categories (never pooled in analysis)

| Code | Category | Count | Purpose |
|------|----------|-------|---------|
| `SD` | Single-domain attacks | 12 | Sanity floor — caught by all arms incl. rules (A4). |
| `KC` | Multi-stage kill chains | 15 | **Primary test of H1/H2; cross-domain correlation required.** |
| `LS` | Low-and-slow evasion | 12 | Temporal correlation; pre-filter recall stress. |
| `EP` | Ephemeral compute | 10 | SQLite state-capture of short-lived resources. |
| `BN` | Benign noise | 10 | FPR measurement; ground truth = **no attack** (empty `stages`). |
| | **Dev-set total** | **59** | |
| `HO` | Held-out validation | 10 | Sealed before system finalisation; selection-bias control. |
| | **Grand total** | **~69** | |

## 2. Quality requirements (v3 §4.3)

- **Real-world grounding:** every scenario cites a documented real AWS incident pattern or ATT&CK-for-Cloud
  procedure in its manifest. (Defends "are your synthetic attacks realistic?")
- **Inter-rater check (NEW):** ≥ 20% of scenarios (≥ 14) are independently reviewed by the team member who did
  **not** author them; disagreements on stage-ordering or TTP mapping are resolved and recorded in the
  manifest `authorship` block (`03`). Candidate review set marked ☑ in the catalog below.
- **Held-out authorship separation (NEW):** `HO-*` scenarios are authored **before** the system's specific
  failure modes are known, and sealed in P2. Document the timeline explicitly.
- **Citation rule:** every `real_incident_reference` is a grounding pointer and **must be confirmed to a
  locatable source** (URL / report / CVE) before the pre-registration is signed.

## 3. TTP grounding & technique set

TTP IDs are grounded in the techniques curated in `tools/mitre_lookup.py`. The three sub-techniques flagged at
freeze — `T1098.001` (Additional Cloud Credentials), `T1548.005` (Temporary Elevated Cloud Access),
`T1562.008` (Disable Cloud Logs) — have since been **added** to `tools/mitre_lookup.py` (now 22 techniques).

---

## 4. Master catalog

Legend: ☑ in **IR** column = candidate for the 20% inter-rater review.

### 4.1 Single-domain (`SD-*`, 12) — Owner: Atishay
| ID | Title | TTP(s) | Telemetry | Grounding | IR |
|----|-------|--------|-----------|-----------|----|
| SD-01 | Public S3 bucket / mass object read | T1530 | S3 | Open-bucket exposures (UpGuard) | ☑ |
| SD-02 | Dangerous security-group port opened | T1190 | CloudTrail | Stratus SG-misconfig (Datadog) | |
| SD-03 | Bulk S3 object deletion | T1485 | S3/CloudTrail | Ransom-style S3 deletion | ☑ |
| SD-04 | EC2 launch in unapproved region | T1578 | CloudTrail/EC2 | Cryptomining region abuse | |
| SD-05 | IMDSv1 credential access | T1552.005 | CloudTrail/EC2 | TeamTNT IMDS theft (Cado) | ☑ |
| SD-06 | Network port scan against subnet | T1046 / T1595 | VPC/Zeek | Active-scanning recon | |
| SD-07 | Console/API brute force | T1110 | CloudTrail | Credential stuffing | |
| SD-08 | S3 bucket encryption disabled | T1530 | CloudTrail/S3 | Misconfig exposure | |
| SD-09 | CloudTrail logging stopped | T1562.008 | CloudTrail | Defense-evasion (StopLogging) | ☑ |
| SD-10 | Mass IAM/resource enumeration | T1526 / T1580 | CloudTrail | Post-compromise discovery | |
| SD-11 | Beaconing on non-standard port | T1571 | VPC/Zeek | C2 beaconing | |
| SD-12 | Bulk Secrets Manager access | T1528 | CloudTrail | Token/secret theft | |

### 4.2 Multi-stage kill chains (`KC-*`, 15) — Owner: Atishay
Each chain exercises **≥ 3 connected stages across ≥ 2 telemetry sources**. Stage outlines in §5.
| ID | Title | Stage TTPs (ordered) | Telemetry | Grounding | IR |
|----|-------|----------------------|-----------|-----------|----|
| KC-01 | Stolen creds → IAM backdoor → S3 exfil | T1078.004→T1098.001→T1530→T1537 | CloudTrail,S3,VPC | Rhino/CloudGoat | ☑ |
| KC-02 | SSRF → IMDS → discovery → S3 exfil | T1552.005→T1580→T1530→T1537 | CloudTrail,EC2,S3,VPC | **Capital One 2019** | ☑ |
| KC-03 | Key → privesc → disable logging | T1078.004→T1548.005→T1098.001→T1562.008 | CloudTrail | Rhino privesc | ☑ |
| KC-04 | Cred theft → lateral AssumeRole → exfil | T1078.004→T1526→T1548.005→T1537 | CloudTrail,VPC | **SCARLETEEL 2023** | ☑ |
| KC-05 | Secrets → discovery → cross-account copy | T1078.004→T1528→T1580→T1537 | CloudTrail,S3 | Token→cross-acct exfil | |
| KC-06 | New IAM user → S3 staging → exfil | T1098→T1530→T1537 | CloudTrail,S3,VPC | Rhino persistence | |
| KC-07 | IMDS → cryptomining launch → impact | T1552.005→T1578→T1496 | CloudTrail,EC2 | TeamTNT cryptojacking | ☑ |
| KC-08 | Brute force → valid acct → disable logs → destroy | T1110→T1078.004→T1562.008→T1485 | CloudTrail,S3 | Stuffing→destruction | |
| KC-09 | Phished creds → console → SG open → exfil | T1078.004→T1190→T1530→T1537 | CloudTrail,S3,VPC | Phishing-for-cloud-creds | |
| KC-10 | Public bucket discovery → mass DL → cross-acct | T1580→T1530→T1537 | CloudTrail,S3,VPC | Open-bucket harvest | |
| KC-11 | Role chaining → secrets → exfil | T1548.005→T1528→T1537 | CloudTrail,S3 | AssumeRole chaining | ☑ |
| KC-12 | Login-profile persistence → privesc → mining | T1098.001→T1548.005→T1496 | CloudTrail,EC2 | Persistence→hijack | |
| KC-13 | Lambda backdoor → creds → S3 exfil | T1098→T1528→T1530→T1537 | CloudTrail,S3,VPC | Serverless backdoor | |
| KC-14 | Snapshot/AMI exfil → cross-account share | T1578→T1537 | CloudTrail,EC2 | EBS-snapshot exfil | |
| KC-15 | Slow compromise → logging-off → destruction | T1078.004→T1098.001→T1562.008→T1485 | CloudTrail,S3 | Long-dwell destructive | ☑ |

### 4.3 Low-and-slow evasion (`LS-*`, 12) — Owner: Anna
| ID | Title | TTP(s) | Telemetry | Grounding | IR |
|----|-------|--------|-----------|-----------|----|
| LS-01 | Slow privilege escalation over days | T1098 / T1548.005 | CloudTrail | Long-dwell APT privesc | ☑ |
| LS-02 | Drip-rate S3 exfiltration | T1530 / T1537 | S3/VPC | Low-and-slow exfil | ☑ |
| LS-03 | Periodic beaconing C2 | T1571 | VPC/Zeek | Beaconing C2 | |
| LS-04 | Staged discovery across sessions | T1526 / T1580 | CloudTrail | Stealthy enumeration | |
| LS-05 | Gradual IAM key creation across users | T1098.001 | CloudTrail | Slow persistence | ☑ |
| LS-06 | Low-volume cross-account copy over weeks | T1537 | S3/VPC | Stealth exfil | |
| LS-07 | Intermittent IMDS cred-refresh abuse | T1552.005 | CloudTrail/EC2 | Cred reuse | |
| LS-08 | Slow SG rule drift opening ports | T1190 | CloudTrail | Config drift abuse | |
| LS-09 | Sporadic brute force then success | T1110 | CloudTrail | Slow stuffing | |
| LS-10 | Long-dwell snapshot sharing | T1578 / T1537 | CloudTrail/EC2 | Snapshot exfil | |
| LS-11 | Periodic secret access blended with legit | T1528 | CloudTrail | Blended theft | |
| LS-12 | Slow log-tampering (rotate off/on) | T1562.008 | CloudTrail | Evasion drift | ☑ |

### 4.4 Ephemeral compute (`EP-*`, 10) — Owner: Anna
Short-lived resources (see `EPHEMERAL_INSTANCE_THRESHOLD` in `config.py`).
| ID | Title | TTP(s) | Telemetry | Grounding | IR |
|----|-------|--------|-----------|-----------|----|
| EP-01 | Spin-up → mine → terminate in minutes | T1496 / T1578 | EC2/CloudTrail | Ephemeral cryptojacking | ☑ |
| EP-02 | Short-lived instance for exfil staging | T1537 | EC2/VPC/S3 | Burner exfil | |
| EP-03 | Transient role assume + immediate revoke | T1548.005 | CloudTrail | Just-in-time abuse | ☑ |
| EP-04 | Spot-instance cryptomining burst | T1496 | EC2/CloudTrail | Spot abuse | |
| EP-05 | Ephemeral Lambda for discovery | T1526 | CloudTrail | Serverless recon | |
| EP-06 | Burner instance port scan then terminate | T1046 | VPC/EC2 | Recon burst | |
| EP-07 | Short-lived instance secrets pull | T1528 | CloudTrail/EC2 | Quick secret theft | |
| EP-08 | Quick AMI copy then deregister | T1578 | CloudTrail/EC2 | Image exfil | |
| EP-09 | Transient access key create+use+delete | T1098.001 | CloudTrail | Ephemeral creds | ☑ |
| EP-10 | Ephemeral instance beacon then terminate | T1571 | VPC/EC2 | Short C2 | |

### 4.5 Benign noise (`BN-*`, 10) — Owner: Anna — **ground truth = no attack** (`stages: []`)
| ID | Title | Telemetry | Why it's a useful FP test | IR |
|----|-------|-----------|---------------------------|----|
| BN-01 | Normal admin day | all | Baseline; zero stages | ☑ |
| BN-02 | Legit bulk data migration | S3/VPC | Looks like exfil, authorised | ☑ |
| BN-03 | Scheduled autoscaling churn | EC2 | Looks ephemeral, benign | |
| BN-04 | CI/CD creating/deleting roles | CloudTrail | Looks like IAM manipulation | ☑ |
| BN-05 | Legit cross-account backup copy | S3 | Looks like cross-acct exfil | |
| BN-06 | Security-team audit enumeration | CloudTrail | Looks like discovery | |
| BN-07 | Planned access-key rotation | CloudTrail | Looks like credential abuse | |
| BN-08 | Batch job large S3 reads | S3 | Looks like mass download | |
| BN-09 | Dev test instances up/down | EC2 | Looks ephemeral | |
| BN-10 | App secrets access at scale | CloudTrail | Looks like secret theft | |

### 4.6 Held-out (`HO-*`, 10) — Owner: Anna — **SEAL IN P2; authored before system finalisation**
| ID | Title | TTP(s) | Telemetry | Mirrors |
|----|-------|--------|-----------|---------|
| HO-01 | Novel cred-theft → privesc → exfil | T1078.004→T1548.005→T1537 | CloudTrail,S3,VPC | multi-stage |
| HO-02 | Unseen single-domain S3 abuse | T1530 | S3 | single-domain |
| HO-03 | Low-and-slow exfil variant | T1530 / T1537 | S3/VPC | low-and-slow |
| HO-04 | Ephemeral cryptomining variant | T1496 | EC2 | ephemeral |
| HO-05 | Benign noisy ops day | — | all | benign |
| HO-06 | Multi-stage with decoy benign sub-sequence | T1078.004→T1098.001→T1485 | CloudTrail,S3 | multi-stage (hard) |
| HO-07 | Novel role-chaining lateral movement | T1548.005→T1526→T1537 | CloudTrail,VPC | multi-stage |
| HO-08 | Single-domain logging-disable variant | T1562.008 | CloudTrail | single-domain |
| HO-09 | Ephemeral Lambda discovery variant | T1526 | CloudTrail | ephemeral |
| HO-10 | Benign migration resembling exfil | — | S3/VPC | benign |

---

## 5. Stage outlines for `KC-*` (ordered: `stage_id`. tactic — `TTP` — log source)

**KC-01** 1.IA `T1078.004` CT · 2.Persist `T1098.001` CT · 3.Collection `T1530` S3 · 4.Exfil `T1537` VPC
**KC-02** *(Capital One)* 1.CredAccess `T1552.005` CT/EC2 · 2.Discovery `T1580` CT · 3.Collection `T1530` S3 · 4.Exfil `T1537` VPC
**KC-03** 1.IA `T1078.004` CT · 2.PrivEsc `T1548.005` CT · 3.Persist `T1098.001` CT · 4.Evasion `T1562.008` CT
**KC-04** *(SCARLETEEL)* 1.IA `T1078.004` CT · 2.Discovery `T1526` CT · 3.Lateral `T1548.005` CT/VPC · 4.Exfil `T1537` VPC
**KC-05** 1.IA `T1078.004` CT · 2.CredAccess `T1528` CT · 3.Discovery `T1580` CT · 4.Exfil `T1537` S3/CT
**KC-06** 1.Persist `T1098` CT · 2.Collection `T1530` S3 · 3.Exfil `T1537` VPC
**KC-07** 1.CredAccess `T1552.005` CT/EC2 · 2.InfraMod `T1578` CT/EC2 · 3.Impact `T1496` EC2
**KC-08** 1.CredAccess `T1110` CT · 2.IA `T1078.004` CT · 3.Evasion `T1562.008` CT · 4.Impact `T1485` S3
**KC-09** 1.IA `T1078.004` CT · 2.Exploit `T1190` CT · 3.Collection `T1530` S3 · 4.Exfil `T1537` VPC
**KC-10** 1.Discovery `T1580` CT · 2.Collection `T1530` S3 · 3.Exfil `T1537` VPC
**KC-11** 1.PrivEsc `T1548.005` CT · 2.CredAccess `T1528` CT · 3.Exfil `T1537` S3
**KC-12** 1.Persist `T1098.001` CT · 2.PrivEsc `T1548.005` CT · 3.Impact `T1496` EC2
**KC-13** 1.Persist `T1098` CT · 2.CredAccess `T1528` CT · 3.Collection `T1530` S3 · 4.Exfil `T1537` VPC
**KC-14** 1.InfraMod `T1578` CT/EC2 · 2.Exfil `T1537` CT
**KC-15** 1.IA `T1078.004` CT · 2.Persist `T1098.001` CT · 3.Evasion `T1562.008` CT · 4.Impact `T1485` S3

---

## 6. Worked manifest examples

Conform to `03_manifest_schema.md` / `manifest.schema.json`. `evidence_event_ids` are **placeholders** (bound
in P2). These are validated against the schema in P1 verification.

### 6.1 Single-domain — `SD-01`
```json
{
  "scenario_id": "SD-01",
  "category": "single_domain",
  "real_incident_reference": "Public S3 bucket exposure (UpGuard-documented open buckets) — VERIFY URL at lock",
  "authorship": {"author": "Atishay", "reviewer": "Anna", "review_date": "TBD", "authored_before_system_final": true},
  "stages": [
    {"stage_id": 1, "ttp_id": "T1530", "ttp_name": "Data from Cloud Storage Object",
     "telemetry_source": "S3", "evidence_event_ids": ["s3-0001","s3-0002","s3-0003"],
     "timestamp_range": ["T+0s","T+45s"]}
  ]
}
```

### 6.2 Multi-stage — `KC-02` (Capital One pattern)
```json
{
  "scenario_id": "KC-02",
  "category": "multi_stage_kill_chain",
  "real_incident_reference": "Capital One breach, 2019 (SSRF -> IMDS -> S3 exfiltration) — VERIFY source at lock",
  "authorship": {"author": "Atishay", "reviewer": "Anna", "review_date": "TBD", "authored_before_system_final": true},
  "stages": [
    {"stage_id": 1, "ttp_id": "T1552.005", "ttp_name": "Unsecured Credentials: Cloud Instance Metadata API",
     "telemetry_source": "CloudTrail", "evidence_event_ids": ["ct-1001"], "timestamp_range": ["T+0s","T+20s"]},
    {"stage_id": 2, "ttp_id": "T1580", "ttp_name": "Cloud Infrastructure Discovery",
     "telemetry_source": "CloudTrail", "evidence_event_ids": ["ct-1015","ct-1016"], "timestamp_range": ["T+25s","T+60s"]},
    {"stage_id": 3, "ttp_id": "T1530", "ttp_name": "Data from Cloud Storage Object",
     "telemetry_source": "S3", "evidence_event_ids": ["s3-2001","s3-2002","s3-2003"], "timestamp_range": ["T+65s","T+140s"]},
    {"stage_id": 4, "ttp_id": "T1537", "ttp_name": "Transfer Data to Cloud Account",
     "telemetry_source": "VPC", "evidence_event_ids": ["vpc-3001"], "timestamp_range": ["T+140s","T+180s"]}
  ]
}
```

### 6.3 Benign — `BN-01` (ground truth = no attack)
```json
{
  "scenario_id": "BN-01",
  "category": "benign",
  "real_incident_reference": "N/A - synthetic benign baseline",
  "stages": []
}
```
