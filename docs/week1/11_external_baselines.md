# External Baselines — Specification

**Owner:** Anna | **Status:** SIGMA built (P3 complete). GuardDuty and LLMCloudHunter **DROPPED** — see §1 and §2.

> **Why this document exists (plain language).** Four-arm ablation (A1–A4) tells you which *internal* part
> helps. A journal also wants to know how you compare to the *existing field*. The community Sigma baseline
> (SIGMA arm, already implemented) removes the reviewer objection "your rules arm was rigged to lose" without
> requiring real-AWS access or a competitor reimplementation.

---

## 1. GuardDuty — DROPPED

**Reason:** GuardDuty requires real-AWS access with a ≥7-day warm-up period. The real-AWS budget has not been
approved by the supervisor (blocking dependency `07` §9), and there is insufficient time to complete this
before submission. Additionally, GuardDuty is not a kill-chain reconstructor — any score would require caveated
interpretation and would not directly address H1 or H2.

**Paper treatment:** One sentence in §7 (Threats to Validity / Limitations): *"GuardDuty comparison is
deferred to a real-AWS follow-up study; the community Sigma baseline (SIGMA arm) already guards against the
'rules arm was designed to lose' objection."*

~~*Original plan: AWS managed threat-detection service, real-AWS only, `GD` arm code.*~~

---

## 2. LLMCloudHunter reimplementation — DROPPED

**Reason:** LLMCloudHunter (Schwartz et al., 2025; arXiv:2407.05194) generates Sigma-style detection *rules*
from CTI reports. It does **not** reconstruct kill chains from live telemetry — the task mismatch means any
benchmark score would compare apples to oranges and invite reviewer criticism. The paper already positions it
correctly in the related-work taxonomy (§2.1: *"targets rule generation, not reconstruction"*). A faithful
reimplementation would be a significant P3 cost for a result that is not directly interpretable under the
matching function (`04`).

**Paper treatment:** Keep the related-work paragraph and the coverage-gap table entry as-is. Add one clause to
§5.1 (Arms and Baselines): *"LLMCloudHunter generates detection rules from CTI reports (a different task from
kill-chain reconstruction over live telemetry) and is therefore positioned in related work rather than run as a
benchmark arm."*

~~*Original plan: partial reimplementation adapted to run over CloudKC-Bench telemetry, `LCH` arm code.*~~

---

## 3. Community Sigma rules correlator — IMPLEMENTED ✅

- **What:** community Sigma rules for AWS CloudTrail + S3 (modelled on SigmaHQ `rules/cloud/aws`), arm code
  `SIGMA`. Implemented in `benchmark/arms/sigma.py`.
- **Why this is sufficient:** removes the reviewer attack "A4 was designed to lose" — an independent,
  community-authored ruleset with no VPC/flow-log coverage (just like real SigmaHQ rules) shows where any
  rules-only approach fails.
- **Coverage note:** no VPC flow-log rules (stated honestly in the paper — this is the point).
- **Provenance:** `SIGMA_RULES` catalogue in `benchmark/arms/sigma.py` lists every rule and its ATT&CK tag.

## 4. Format-parity requirement

SIGMA emits the identical reconstructed-chain schema as A1–A4 via `correlate.build_chain`. The matching
function (`04`) scores it without special-casing.

| Baseline | Arm code | Environment | LLM cost | Status |
|----------|----------|-------------|----------|--------|
| GuardDuty | `GD` | real_aws only | none | **DROPPED** (budget-gated) |
| LLMCloudHunter reimpl | `LCH` | localstack + real_aws | yes | **DROPPED** (task mismatch) |
| Community Sigma | `SIGMA` | localstack + real_aws | none | **DONE** |
