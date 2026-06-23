#!/usr/bin/env python3
"""
CloudKC-Bench — a-priori power analysis (v3 journal, Section 7.3).

Computes the required number of scenarios PER CATEGORY (the unit of analysis is
the scenario, not the trial) to detect a given effect at 80% power, for the
primary hypothesis tests. Arms run on the SAME scenarios, so H1/H2 are PAIRED
comparisons -> a one-sample test on the per-scenario differences. The relevant
effect size is Cohen's dz (standardized mean of the paired differences).

We report required n both UNCORRECTED (alpha = 0.05) and after a conservative
Holm-Bonferroni planning bound (alpha / m, the worst-case smallest threshold
across the ~100-test comparison grid). The conservative bound is what we
pre-register against so the experiment is not underpowered after correction.

Run:  python3 power_analysis.py
Deps: statsmodels, scipy   (pip install statsmodels scipy)
"""
import math

try:
    from statsmodels.stats.power import TTestPower
    HAVE_SM = True
except Exception:  # pragma: no cover - fallback if statsmodels missing
    HAVE_SM = False

ALPHA = 0.05
POWER = 0.80
M_TESTS = 100          # ~ metric x category x arm comparison grid (v3 ~100)
EFFECTS = {            # Cohen's dz (paired) -> label
    0.5: "medium",
    0.8: "large",
    1.0: "very large",
    1.2: "huge",
}


def required_n_paired(dz, alpha, power):
    """Required n for a two-sided one-sample (paired) t-test."""
    if HAVE_SM:
        n = TTestPower().solve_power(effect_size=dz, alpha=alpha,
                                     power=power, alternative="two-sided")
        return math.ceil(n)
    # Normal-approx fallback (slightly optimistic; statsmodels is preferred)
    from scipy.stats import norm
    z_a = norm.ppf(1 - alpha / 2)
    z_b = norm.ppf(power)
    return math.ceil(((z_a + z_b) / dz) ** 2)


def main():
    alpha_corr = ALPHA / M_TESTS
    print(f"Engine: {'statsmodels' if HAVE_SM else 'normal-approx fallback'}")
    print(f"alpha (uncorrected) = {ALPHA}, power = {POWER}")
    print(f"Holm-Bonferroni planning bound: alpha/m = {ALPHA}/{M_TESTS} = {alpha_corr:.5f}")
    print(f"Design: paired (arms share scenarios) -> one-sample t-test on differences\n")
    print(f"{'dz':>5} {'effect':>11} {'n (uncorr)':>12} {'n (corrected)':>14}")
    print("-" * 46)
    rows = {}
    for dz, label in EFFECTS.items():
        n_unc = required_n_paired(dz, ALPHA, POWER)
        n_cor = required_n_paired(dz, alpha_corr, POWER)
        rows[dz] = (label, n_unc, n_cor)
        print(f"{dz:>5} {label:>11} {n_unc:>12} {n_cor:>14}")

    print("\nPlanned per-category dev-set n (v3 Section 4.2):")
    planned = {"single_domain": 12, "multi_stage_kill_chain": 15,
               "low_and_slow": 12, "ephemeral": 10, "benign": 10}
    for cat, n in planned.items():
        print(f"  {cat:<24} n = {n}")

    # Verdict against the corrected requirement
    min_detectable = None
    for dz in sorted(EFFECTS):
        if rows[dz][2] <= min(planned.values()):
            min_detectable = dz
            break
    print("\nVerdict (corrected, power=0.80):")
    if min_detectable:
        print(f"  Smallest effect detectable at n={min(planned.values())} (smallest category): "
              f"dz >= {min_detectable} ({EFFECTS[min_detectable]}).")
    else:
        print(f"  Even dz=1.2 needs n>{min(planned.values())} after correction; "
              f"smallest categories are descriptive-only.")
    print("  => Categories whose planned n is below the corrected requirement for the "
          "pre-registered effect are reported DESCRIPTIVE-ONLY (no significance testing).")


if __name__ == "__main__":
    main()
