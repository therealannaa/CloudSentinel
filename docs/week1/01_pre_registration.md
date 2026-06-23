# Pre-Registration — CloudKC-Bench

**Owner:** Atishay (drafts) · Anna (co-signs) | 🔒 **FREEZE-FIRST**
**Status:** DRAFT — awaiting co-sign and date

> **v3 (journal) — changed from v2:** RQ/H1/H2 are **unchanged**. Added: (a) the **formal power analysis**
> (`08_power_analysis.md`) is a required, frozen input — categories below the computed n-threshold are
> reported **descriptive-only** (no significance testing); (b) **dual-environment** reporting — real-AWS
> results are the headline, LocalStack results are the reproducibility check; (c) the H1 margin must be
> consistent with the minimum detectable effect from `08`.

> **Why this document exists (plain language).** A pre-registration is a public, dated promise about *what
> we will measure and what counts as success* — written **before** we have any results. It is the single most
> important defence against the "you moved the goalposts after seeing the data" criticism that sinks
> security-ML papers. Once Atishay and Anna both sign and date the bottom of this file, the numbers in it do
> **not** change. If the data later disagrees with our hypotheses, we report that honestly — a refuted
> hypothesis is still a publishable finding.

---

## 1. Research Question (RQ)

> Given heterogeneous AWS control-plane and network telemetry (CloudTrail/IAM API events, VPC Flow Logs, S3
> access logs, EC2 lifecycle events) produced during a multi-stage attack, **does an LLM cross-domain
> correlation layer reconstruct the kill chain more accurately than (a) a single generalised LLM agent and
> (b) a deterministic rules-only correlator — and under what conditions?**

The unit of the claim is the **reconstructed kill chain** (ordered stages, each with a TTP ID and supporting
evidence events), scored by a mechanical matching function (see `04_matching_function_spec.md`) against a
ground-truth manifest (see `03_manifest_schema.md`).

## 2. The four arms (the causal core)

These are *configurations of the system*, identical in everything except the one variable under test.

| Arm | Configuration | Isolates |
|-----|---------------|----------|
| **A1** | Pre-filter + 4 domain hunters + coordinator (full CloudSentinel, CrewAI) | — |
| **A2** | Pre-filter + single generalised LLM agent | A1 vs A2 → multi-agent decomposition (H2) |
| **A3** | No pre-filter + single agent on raw logs | A2 vs A3 → the pre-filter (C3) |
| **A4** | Pre-filter + deterministic rules only, **NO LLM** | A1/A2 vs A4 → value of the LLM (H1) |

## 3. Hypotheses (with pre-set, falsifiable thresholds)

### H1 — LLM vs rules *(primary, directional)*
> **The LLM arms (A1 and A2) achieve higher multi-stage-category recall than the rules-only arm (A4), by a
> pre-registered margin.**

- **Primary metric:** Recall (TPR) on the **multi-stage kill-chain category only** (`KC-*` scenarios).
- **Pre-registered margin (TO BE CO-SIGNED):** the better of {A1, A2} exceeds A4 by **≥ 0.15 absolute
  recall**, with the 95% bootstrap CI of the difference excluding 0. *This margin must be ≥ the minimum
  detectable effect computed in `08_power_analysis.md` at the frozen per-category n; if `08` shows 0.15 is
  undetectable at our n, raise n or relax the margin **before** sign-off.*
- **Decision:** *Supported* if the margin and CI condition both hold; otherwise *Refuted*. If A4 (rules-only)
  matches the LLM, the LLM's value evaporates — and **reporting that is itself the scientific contribution.**

### H2 — Multi-agent vs single-agent *(stated as a null, on purpose)*
> **Multi-agent decomposition (A1) does NOT outperform a single generalised LLM agent (A2) on identical
> inputs.**

- **Primary metric:** F1 on the multi-stage category, A1 vs A2 (same model, same telemetry, same compute).
- **Equivalence / decision rule (TO BE CO-SIGNED):** if |A1 − A2| F1 < **0.05** and the 95% CI of the
  difference includes 0, we **fail to reject** H2 (decomposition adds no measurable value — publishable). If
  A1 − A2 ≥ **0.05** with CI excluding 0, we **reject** H2 (decomposition helps — publishable). Reported
  honestly either way.

### C3 — Pre-filter contribution *(descriptive, no pass/fail)*
A2 vs A3 quantifies what the deterministic pre-filter contributes to **cost (tokens), latency, and recall**.
No threshold; reported as measured trade-off (the filtering ratio and pre-filter recall are measured results,
not assumptions).

## 4. Frozen evaluation protocol (no deviation after sign-off)

1. **Unit of analysis = scenario, never trial.** 3 seeds are *repeated measures* of one scenario, not 3
   independent observations. Aggregate to scenario level (mean/median across seeds) or use a mixed-effects
   model with scenario as the random effect. **No "24 × 3 = 72 independent observations."**
2. **Per-category analysis — never pooled.** The five categories (single-domain, multi-stage, low-and-slow,
   ephemeral, benign) are heterogeneous. Every metric is reported per category.
3. **Effect sizes + bootstrap CIs are primary; p-values secondary.** Report Cohen's d and 95% bootstrap CIs.
   A statistically significant but tiny effect is reported as tiny.
4. **Holm-Bonferroni** multiplicity correction across the metric × category × arm grid (~100 tests).
5. **Multi-seed variance — no fake determinism.** Pin the exact model version + date; run **≥ 3 seeds**;
   report run-to-run variance. Do **not** fix a single seed.
6. **Held-out set scored separately**, after all tuning is final (see `02_scenario_taxonomy.md`).
7. **Pre-registered thresholds only.** The margins in §3 are fixed here, in writing, before any result. No
   "expected results" tables predicting deltas.
8. **Null results are publishable.** H2 is a null; confirming or refuting it is a finding. The paper does not
   depend on CloudSentinel "winning."

## 5. Primary metrics (carry the argument)

TPR/Recall, FPR, Precision, F1, AUC, MTTD where meaningful — directly comparable to prior detection work.
Bespoke metrics (KCRS, SFS) are **exploratory only**, reported with caveats, **not** in the abstract, **not**
a contribution.

## 6. Held-fixed configuration (identical across A1–A4)

- **Model:** pinned LLM version + date — `__________________________` *(fill at lock time; the repo currently
  references Gemini via `GEMINI_API_KEY` in `config.py`)*.
- **Telemetry input:** identical scenario set and log volume per arm.
- **Compute budget:** identical token/time budget per arm — `__________________________`.
- **Pre-filter rule set:** frozen reference — `__________________________`.
- **Seed list:** `__________________________` *(≥ 3 seeds; values, not just count, recorded here)*.
- **Threat-intel enrichers (VirusTotal/AbuseIPDB): DISABLED** in all controlled runs.

## 7. Sign-off

By signing, both team members agree the RQ, hypotheses, thresholds (§3), and protocol (§4) are frozen and
will not be altered after the date below. Any change requires Dr. Nagasundari's approval and must be recorded
as a dated amendment beneath this block.

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Author | Atishay | __________ | ______ |
| Co-signer | Anna | __________ | ______ |
| Supervisor (noted) | Dr. S. Nagasundari | __________ | ______ |

### Amendments (post-sign-off, supervisor-approved only)
_None yet._
