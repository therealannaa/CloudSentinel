# External Baselines — Specification

**Owner:** Anna | **Status:** DRAFT spec (built in P3). LLMCloudHunter scope pending supervisor (`07` §10).

> **Why this document exists (plain language).** Four-arm ablation (A1–A4) tells you which *internal* part
> helps. A journal also wants to know how you compare to the *existing field*. v3 requires three external
> baselines so reviewers can position your work — and so nobody can say "your rules arm (A4) was rigged to
> lose." Each baseline must be scored by the **same mechanical matching function** (`04`), via a documented
> adapter if its native output differs.

---

## 1. GuardDuty (real-AWS, primary external baseline)

- **What:** AWS's managed threat-detection service. Run on the real-AWS sandbox (`10`) with the ≥7-day
  warm-up. Not available on LocalStack — real-AWS only.
- **Scope:** run on all scenario categories that the budget supports (prioritise the 15 multi-stage `KC-*`).
- **Adapter:** map GuardDuty findings (finding type, resource, timestamp) → reconstructed-chain stages
  (`ttp_id` via GuardDuty-finding-type→ATT&CK mapping, `telemetry_source`, evidence, `timestamp_range`). The
  mapping table is frozen and published.
- **Caveats:** GuardDuty is not a kill-chain reconstructor; report it as a detection-coverage comparison with
  explicit caveats, never as an apples-to-apples chain-reconstruction score.

## 2. LLMCloudHunter reimplementation (closest competitor)

- **What:** reimplement the core correlation approach of Schwartz et al., 2025 (ACM Web Conf;
  **arXiv:2407.05194**) — LLM generation of Sigma-style detections from CTI — adapted to run over
  CloudKC-Bench telemetry.
- **Scope (supervisor decision, `07` §10):** a **faithful partial** reimplementation with **documented
  deviations** is acceptable and normal in benchmark papers; full reimplementation is a larger P3 cost.
- **Adapter:** its detections → reconstructed-chain stages, same schema as the arms.
- **Honesty:** state every deviation from the original in the paper; cite the source precisely.

## 3. Community Sigma rules correlator (de-risks A4)

- **What:** published **community Sigma rules for AWS CloudTrail** (e.g. the SigmaHQ `cloud/aws` ruleset) used
  to supplement or replace the team-authored A4 rules.
- **Why:** removes the reviewer attack "the rules-only arm was designed to lose." If community rules match the
  LLM, that *strengthens* the H1 finding's credibility.
- **Adapter:** Sigma match → reconstructed-chain stage (`ttp_id` from the rule's ATT&CK tag).
- **Provenance:** pin the exact ruleset commit/version; list which rules fired per scenario.

## 4. Format-parity requirement (shared)

All three baselines must emit — directly or through their frozen adapter — the **identical reconstructed-chain
schema** the arms use, or the matching function (`04`) rejects the run. Adapters are part of the released
artifact so the comparison is reproducible and not format-confounded.

| Baseline | Arm code (`05`) | Environment | LLM cost |
|----------|-----------------|-------------|----------|
| GuardDuty | `GD` | real_aws | none |
| LLMCloudHunter reimpl | `LCH` | localstack + real_aws | yes (tracked) |
| Community Sigma | `SIGMA` | localstack + real_aws | none |
