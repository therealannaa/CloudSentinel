# Formal A-Priori Power Analysis — CloudKC-Bench

**Owner:** Atishay | 🔒 **FREEZE-FIRST** (write & freeze BEFORE any experiment runs — v3 §7.3)
**Reproduce:** `python3 docs/week1/power_analysis.py` (needs `statsmodels`, `scipy`)
**Status:** DRAFT — numbers below are computed; the *chosen* primary-test set is co-signed at the sync.

> **Why this document exists (plain language).** "Power" is the probability your experiment detects a real
> effect if one exists. A journal *requires* you to show — before collecting data — that your planned number
> of scenarios is large enough to detect the effects you care about. Writing it after the fact is not
> credible. This analysis computes the required scenarios-per-category and, importantly, surfaces an honest
> problem with the v3 plan's assumption.

---

## 1. Design facts that drive the math

- **Unit of analysis = scenario**, not trial (repeated seeds are repeated measures; aggregate to scenario).
- **Arms share scenarios**, so H1 (LLM vs rules) and H2 (multi-agent vs single) are **paired** comparisons →
  a one-sample t-test on the per-scenario differences. The effect size is **Cohen's dz** (standardized mean
  of the paired differences).
- **α = 0.05, power = 0.80** (standard).
- **Multiplicity:** the full comparison grid is ~**100 tests** (metric × category × arm). Holm-Bonferroni
  controls family-wise error; for *planning* we use the conservative worst-case threshold **α/m**.

## 2. Computed requirements (from `power_analysis.py`)

Required scenarios per category for a paired test at power 0.80:

| Effect (dz) | Label | n (uncorrected, α=0.05) | n (corrected, α=0.0005, m=100) |
|-------------|-------|-------------------------|--------------------------------|
| 0.5 | medium | 34 | **81** |
| 0.8 | large | 15 | **36** |
| 1.0 | very large | 10 | **25** |
| 1.2 | huge | 8 | **19** |

Planned dev-set n per category (v3 §4.2): single-domain 12, **multi-stage 15**, low-and-slow 12,
ephemeral 10, benign 10.

## 3. The honest finding (this contradicts v3 §4.1)

> **v3 §4.1 claims "n ≥ 12 per category is needed to detect moderate effects at 80% power after correction."
> The computation shows that is false for a 100-test grid.** After Holm-Bonferroni across ~100 tests, even a
> **huge** effect (dz = 1.2) needs n = 19 — and our largest category (multi-stage, n = 15) still falls short.
> A *moderate* effect (dz = 0.5) needs **n = 81**, far beyond the entire ~70-scenario benchmark. At the
> planned n, a fully-corrected per-category significance test can detect **only very-large effects, and even
> then most categories are underpowered.**

This is not a reason to abandon the benchmark — it is a reason to **plan the statistics honestly**.

## 4. Resolution — the lever is the number of *primary* tests (m)

The crippling factor is m = 100, not n. We do **not** need 100 confirmatory tests. The fix is to
**pre-register a small set of PRIMARY confirmatory tests** and treat everything else as exploratory. Required
n as a function of m (from `power_analysis.py`'s companion computation):

| m (primary tests) | corrected α | n for dz=0.8 (large) | n for dz=1.0 |
|-------------------|-------------|----------------------|--------------|
| 1 | 0.0500 | 15 | 10 |
| **2** | 0.0250 | 18 | **13** |
| 4 | 0.0125 | 21 | 15 |
| 5 | 0.0100 | 22 | 16 |
| 100 | 0.0005 | 36 | 25 |

**Pre-registered plan (to co-sign at the sync):**
1. **Primary confirmatory tests = 2:** (i) H1 — best-LLM vs A4 recall on the **multi-stage** category; (ii)
   H2 — A1 vs A2 F1 on the **multi-stage** category. Correct only across these two (m = 2).
2. At m = 2, the multi-stage category (n = 15) is powered for **dz ≥ ~1.0 (very large)** effects (needs 13);
   it is *not* powered for large/medium effects — state this limit explicitly.
3. **Everything else** (other categories, other metrics, other arm pairs) is **exploratory/descriptive**:
   reported with **effect sizes + bootstrap 95% CIs** (which v3 §7.2 already makes primary), **no** family-wise
   significance claim.
4. Any category/metric below its corrected requirement for the chosen effect is labelled **descriptive-only**
   in the results — never significance-tested.

> **Consequence for the pre-registration (`01`).** The H1 margin (default +0.15 recall) is a *practical*
> threshold; the *statistical* detectability at n = 15, m = 2 corresponds to a very-large standardized effect.
> If the team wants to claim a *moderate* effect with corrected significance, the only honest options are:
> raise multi-stage n toward ~18–20, or accept the descriptive-only framing. Decide at sign-off.

## 5. What goes verbatim in the paper (Methods)

> "We conducted an a-priori power analysis (paired design, α = 0.05, power = 0.80). Across the full
> metric × category × arm grid (~100 comparisons) no category reaches the corrected n for moderate effects;
> we therefore pre-registered two primary confirmatory tests (H1 and H2 on the multi-stage category), powered
> for very-large effects at n = 15, and report all other comparisons as exploratory with effect sizes and
> bootstrap confidence intervals. Categories below the corrected n-threshold are descriptive-only."

This frozen statement, plus the per-category n table (§2) and the primary-test set (§4), constitute the
pre-registered power analysis. **Do not change after data collection begins.**
