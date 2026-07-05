# Coverage Gap Table — C1 Novelty Defence

**Owner:** Anna | **Status:** DRAFT filled from paper abstracts + author summaries (Jul 2026). Confirm the
`Partial` cells against the **full text** before final submission (per docs rule "read the actual papers").

> **Why this document exists (plain language).** Contribution C1 claims CloudKC-Bench is the *first* open
> benchmark targeting AWS control-plane multi-stage kill chains specifically. A reviewer connected to any
> competing project will check this claim cell by cell. This table is the evidence: six properties × six
> benchmarks, each cell backed by a located source.

---

## The table (v3 §4.4)

Legend: ✅ yes · ❌ no · ◐ partial. Sources in the per-paper notes below.

| Property | CyberSOCEval | ExCyTIn-Bench | OrgForge-IT | LLMCloudHunter | ACSE-Eval | **CloudKC-Bench (ours)** |
|---|---|---|---|---|---|---|
| AWS control-plane specific | ❌ | ❌ | ❌ | ◐ | ◐ | ✅ |
| Multi-stage kill chains | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Open + reproducible | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| Machine-checkable ground truth | ◐ | ✅ | ✅ | ❌ | ◐ | ✅ |
| ATT&CK-for-Cloud mapped | ❌ | ❌ | ❌ | ◐ | ◐ | ✅ |
| Real-AWS validated | ❌ | ❌ | ❌ | ❌ | ❌ | ◐ |

## Per-paper evidence

- **CyberSOCEval** — arXiv:2509.20166 (Meta CyberSecEval 4, 2025); github.com/CrowdStrike/CyberSOCEval_data.
  Tasks are **Malware Analysis + Threat-Intelligence Reasoning**, not AWS kill chains → ❌ AWS-control-plane,
  ❌ multi-stage kill chains, ❌ ATT&CK-for-Cloud, ❌ real-AWS. Open source → ✅. Scoring method not detailed in
  abstract (task-level accuracy/reward) → ◐ machine-checkable.

- **ExCyTIn-Bench** — arXiv:2507.14201 (ICML 2026); github.com/microsoft/SecRL. **Azure** controlled tenant, 57
  Microsoft Sentinel log tables → ❌ AWS-control-plane, ❌ real-AWS. Multi-hop threat-investigation graphs over
  multi-step attacks → ✅ multi-stage (but framed as **QA over investigation graphs**, not kill-chain
  reconstruction — the task distinction, not a coverage cell). Automatic graph-derived ground truth → ✅
  machine-checkable. Open code/data → ✅. No ATT&CK mapping mentioned → ❌.

- **OrgForge-IT** — arXiv:2603.22499 (Mar 2026). **Insider-threat** detection over multi-surface organizational
  behavioral telemetry (51-day stream) → ❌ AWS-control-plane, ❌ cloud kill chains, ❌ ATT&CK-for-Cloud, ❌
  real-AWS (deterministic synthetic org simulation). Deterministic ("architectural guarantee") ground truth →
  ✅ machine-checkable; verifiable open benchmark + leaderboard → ✅.

- **LLMCloudHunter** — arXiv:2407.05194 (ACM Web Conf 2025). Generates **Sigma detection-rule candidates** from
  CTI reports → ❌ multi-stage kill-chain reconstruction. Cloud-generic with AWS examples → ◐ AWS. Sigma rules
  carry ATT&CK tags → ◐ ATT&CK-for-Cloud. Evaluated on **12 annotated threat reports** (human-annotated CTI),
  not a released benchmark with machine-checkable manifests → ❌ open-benchmark, ❌ machine-checkable, ❌
  real-AWS telemetry.

- **ACSE-Eval** — arXiv:2505.11565 (May 2025; Springer chapter). 100 production-grade **AWS** deployment
  scenarios, 146 AWS services → ◐ AWS (but the task is **threat-modeling of architecture / IaC**, STRIDE +
  ATT&CK + OWASP, not control-plane *telemetry*). Not kill-chain reconstruction from telemetry → ❌ multi-stage
  kill chains. Uses ATT&CK among frameworks → ◐ ATT&CK-for-Cloud. Dataset released → ✅ open. 115 documented
  threats as reference → ◐ machine-checkable. Evaluated on architecture specs, not live AWS telemetry → ❌
  real-AWS validated.

## Decision (C1 verdict)

**No competitor satisfies all six properties**, so the C1 wording stands:

> CloudKC-Bench is the **first open benchmark targeting AWS control-plane multi-stage kill-chain
> reconstruction** with machine-checkable ground-truth manifests and a published mechanical matching function.

Precise distinctions to state in Related Work:
- **ACSE-Eval** is the closest on *AWS-specificity*, but it evaluates **threat modeling of architectures/IaC**,
  not kill-chain reconstruction from control-plane telemetry — a different task.
- **ExCyTIn-Bench** is the closest on *multi-stage + machine-checkable + reproducible*, but it is **Azure** and
  frames the task as **QA over investigation graphs**, not stage-level kill-chain reconstruction.
- **OrgForge-IT** is the closest on *deterministic verifiable ground truth*, but targets **insider threat**, not
  AWS cloud kill chains.
- **LLMCloudHunter** produces **detection rules**, not reconstructed chains, and is not a released benchmark.

> **Honesty caveat:** the ◐ cells (LLMCloudHunter AWS/ATT&CK; ACSE-Eval AWS/ATT&CK/ground-truth) and the
> ExCyTIn "multi-stage" cell rest on abstracts + author summaries. Confirm them against the full papers before
> submission; the "first" claim is robust either way (the ❌ cells that break each competitor are unambiguous:
> platform, task, or real-AWS telemetry).
