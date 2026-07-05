# Threats to Validity (Journal-Tier)

**Owner:** shared | **Status:** LIVING DOC — stated up front in the paper (v3 §10), revisited each phase.

> **Why this document exists (plain language).** Journals expect you to name your own weaknesses before a
> reviewer does, and pair each with a concrete mitigation. Stating them up front is a credibility signal, not
> a confession. This is the v3-expanded version of the v2 list.

---

| Threat | Type | Mitigation (where it lives) |
|--------|------|------------------------------|
| Synthetic scenarios may not generalise to production AWS | External validity | Real-incident grounding per scenario (`02`); **real-AWS as primary environment** (`10`) — v3 upgrade |
| Same team authors scenarios *and* builds the system | Authorship bias | Held-out set frozen before finalisation; **inter-rater check on ≥20%** of scenarios (`02`, manifest `authorship` block) — v3 upgrade |
| KCRS/SFS reward narrative conformity over detection | Construct validity | Standard metrics primary; bespoke metrics explicitly exploratory (`01` §5) |
| LLM non-determinism | Internal validity | Pinned model version+date; **multi-seed runs**; reported variance (`01` §4) |
| Gemini version deprecation | Reproducibility | Record exact version/date; release all artifacts; stated standing limitation |
| **Underpowered statistics in small categories** | Statistical validity | **Formal power analysis pre-registered** (`08`); only 2 primary confirmatory tests; sub-threshold categories descriptive-only — v3 upgrade |
| Threat model excludes adversarial LLM evasion | Construct validity | Explicitly scoped out + justified as a separate research question (v3 §6.3); future work |
| A4 rules "designed to lose" | Internal validity | **Community Sigma rules** baseline supplements/replaces team rules (`11`) — v3 upgrade |
| Single research group, no external validation | External validity | Stated limitation; **open benchmark release** enables future external validation (`10`, artifact) |
| Baseline output format differs from arms | Construct validity | Frozen, published **adapters** map every baseline onto the matching-function schema (`04`, `11`) |
| LocalStack ≠ real AWS (timing, delivery) | External validity | **Dual-environment** clock model (`06`); real-AWS headline, LocalStack reproducibility check |

## Scoping note to write as prose (v3 §6.3)

Each out-of-scope item (adversarial LLM evasion, data-plane attacks, multi-account lateral movement, insider
threats) gets **one justifying paragraph**, not just a list. For adversarial LLM evasion specifically: "We
focus on detection accuracy under cooperative-telemetry assumptions. Adversarial evasion of LLM-based
detectors is an active, separate research question requiring a different (red-team vs detector) design; we
scope it out for experimental tractability and defer it to future work."
