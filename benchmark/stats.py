"""P4 statistics — turns raw per-run scores into journal-grade results.

Implements the frozen protocol (docs/week1/01 pre-registration, docs/week1/08 power
analysis):
  - unit of analysis = scenario: seeds are averaged to a per-scenario value FIRST
  - arms share scenarios -> comparisons are PAIRED (per-scenario differences)
  - effect sizes (Cohen's dz) + bootstrap 95% CIs are PRIMARY; p-values secondary
  - exactly TWO pre-registered primary confirmatory tests, Holm-Bonferroni corrected:
        H1: best{A1,A2} recall  vs  A4 recall   on the multi-stage category
        H2: A1 F1  vs  A2 F1                     on the multi-stage category
  - per-category, NEVER pooled

No numpy/scipy dependency: the p-value is an exact-ish paired sign-flip permutation
test (stdlib only), so this runs with requirements-bench.txt.
"""
from __future__ import annotations

import math
import random
import statistics
from collections import defaultdict

from benchmark import state_cache

PRIMARY_CATEGORY = "multi_stage_kill_chain"
LLM_ARMS = ("A1", "A2")
RULES_ARM = "A4"


# --- loading -----------------------------------------------------------------

def load_results(db_path, environment=None):
    """Load per-run scored results from the state cache into the dict shape that
    experiment.run_experiment also returns."""
    conn = state_cache.connect(db_path)
    q = ("SELECT r.arm, r.scenario_id, sc2.category, r.seed, "
         "       s.recall, s.precision, s.f1 "
         "FROM scores s JOIN runs r ON r.run_id = s.run_id "
         "JOIN scenarios sc2 ON sc2.scenario_id = r.scenario_id")
    args = ()
    if environment:
        q += " WHERE r.environment = ?"
        args = (environment,)
    rows = conn.execute(q, args).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- aggregation -------------------------------------------------------------

def scenario_means(results, metric):
    """{(arm, scenario_id): mean-over-seeds of `metric`}."""
    acc = defaultdict(list)
    for r in results:
        acc[(r["arm"], r["scenario_id"])].append(r[metric])
    return {k: statistics.mean(v) for k, v in acc.items()}


def _category_of(results):
    return {r["scenario_id"]: r["category"] for r in results}


def paired_differences(results, arm_a, arm_b, category, metric):
    """Per-scenario (arm_a - arm_b) differences within `category` (paired design).
    Returns (scenario_ids, diffs)."""
    means = scenario_means(results, metric)
    cat = _category_of(results)
    scen = sorted({s for (a, s) in means if a == arm_a and cat.get(s) == category}
                  & {s for (a, s) in means if a == arm_b})
    diffs = [means[(arm_a, s)] - means[(arm_b, s)] for s in scen]
    return scen, diffs


# --- primitives --------------------------------------------------------------

def bootstrap_ci(values, n_boot=10000, ci=0.95, seed=0):
    """Percentile bootstrap CI of the mean. Resamples the unit (scenarios)."""
    values = list(values)
    if not values:
        return (0.0, 0.0, 0.0)
    point = statistics.mean(values)
    if len(values) == 1:
        return (point, point, point)
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(n_boot):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((1 - ci) / 2 * n_boot)]
    hi = means[int((1 + ci) / 2 * n_boot) - 1]
    return (round(lo, 4), round(hi, 4), round(point, 4))


def cohens_dz(diffs):
    """Paired effect size: mean(diff) / sd(diff)."""
    diffs = list(diffs)
    if len(diffs) < 2:
        return 0.0
    sd = statistics.stdev(diffs)
    if sd == 0:
        return 0.0 if statistics.mean(diffs) == 0 else math.inf
    return round(statistics.mean(diffs) / sd, 4)


def permutation_pvalue(diffs, n_perm=10000, seed=0):
    """Two-sided paired sign-flip permutation test on the mean difference.
    Dependency-free alternative to a paired t / Wilcoxon test."""
    diffs = [d for d in diffs]
    if not diffs:
        return 1.0
    obs = abs(sum(diffs) / len(diffs))
    if obs == 0:
        return 1.0
    rng = random.Random(seed)
    count = 0
    n = len(diffs)
    for _ in range(n_perm):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs)
        if abs(s / n) >= obs - 1e-12:
            count += 1
    return round((count + 1) / (n_perm + 1), 4)


def compare(results, arm_a, arm_b, category, metric, seed=0):
    """Full paired comparison arm_a vs arm_b. Positive `point` favours arm_a."""
    scen, diffs = paired_differences(results, arm_a, arm_b, category, metric)
    lo, hi, point = bootstrap_ci(diffs, seed=seed)
    return {
        "arm_a": arm_a, "arm_b": arm_b, "category": category, "metric": metric,
        "n_scenarios": len(scen), "mean_diff": point,
        "ci95": [lo, hi], "ci_excludes_0": (lo > 0 or hi < 0),
        "cohens_dz": cohens_dz(diffs), "p_perm": permutation_pvalue(diffs, seed=seed),
    }


def holm_bonferroni(pvalues, alpha=0.05):
    """Holm-Bonferroni step-down. Returns list of {p, adj_threshold, reject} in the
    INPUT order."""
    indexed = sorted(range(len(pvalues)), key=lambda i: pvalues[i])
    m = len(pvalues)
    out = [None] * m
    still = True
    for rank, i in enumerate(indexed):
        thr = alpha / (m - rank)
        reject = still and pvalues[i] <= thr
        if not reject:
            still = False
        out[i] = {"p": pvalues[i], "adj_threshold": round(thr, 5), "reject": reject}
    return out


# --- the two pre-registered primary tests ------------------------------------

def evaluate_h1(results, margin=0.15, category=PRIMARY_CATEGORY, seed=0):
    """H1: the better LLM arm beats A4 on recall by >= margin, CI excluding 0."""
    means = scenario_means(results, "recall")
    cat = _category_of(results)
    scen = [s for (a, s) in means if a == RULES_ARM and cat.get(s) == category]
    best, best_mean = None, -1.0
    for arm in LLM_ARMS:
        vals = [means[(arm, s)] for s in scen if (arm, s) in means]
        if vals and statistics.mean(vals) > best_mean:
            best, best_mean = arm, statistics.mean(vals)
    cmp = compare(results, best, RULES_ARM, category, "recall", seed=seed)
    supported = cmp["mean_diff"] >= margin and cmp["ci95"][0] > 0
    return {"hypothesis": "H1", "test": f"best{{A1,A2}}={best} vs A4 recall ({category})",
            "margin": margin, **cmp,
            "verdict": "SUPPORTED" if supported else "NOT SUPPORTED",
            "interpretation": ("LLM beats rules by the pre-registered margin"
                               if supported else
                               "LLM does NOT beat rules by the margin (rules-competitive)")}


def evaluate_h2(results, band=0.05, category=PRIMARY_CATEGORY, seed=0):
    """H2 (null): multi-agent (A1) does NOT outperform single-agent (A2) on F1."""
    cmp = compare(results, "A1", "A2", category, "f1", seed=seed)
    within = abs(cmp["mean_diff"]) < band and not cmp["ci_excludes_0"]
    if within:
        verdict, interp = "FAIL TO REJECT", "multi-agent adds no measurable value (null holds)"
    elif cmp["mean_diff"] >= band and cmp["ci95"][0] > 0:
        verdict, interp = "REJECT", "multi-agent (A1) outperforms single-agent (A2)"
    else:
        verdict, interp = "REJECT", "A1 and A2 differ (A2 >= A1 or large gap)"
    return {"hypothesis": "H2", "test": f"A1 vs A2 F1 ({category})", "band": band,
            **cmp, "verdict": verdict, "interpretation": interp}


# --- per-category exploratory table (with CIs) -------------------------------

def per_category_table(results, metric="recall", seed=0):
    means = scenario_means(results, metric)
    cat = _category_of(results)
    by_arm_cat = defaultdict(list)
    for (arm, s), v in means.items():
        by_arm_cat[(arm, cat[s])].append(v)
    rows = []
    for (arm, category), vals in sorted(by_arm_cat.items()):
        lo, hi, point = bootstrap_ci(vals, seed=seed)
        rows.append({"arm": arm, "category": category, "metric": metric,
                     "n_scenarios": len(vals), "mean": point, "ci95_low": lo, "ci95_high": hi})
    return rows


# --- orchestration -----------------------------------------------------------

def full_report(db_path=None, results=None, environment=None,
                h1_margin=0.15, h2_band=0.05, seed=0):
    if results is None:
        results = load_results(db_path, environment=environment)
    if not results:
        return {"error": "no scored runs found — run `run-arms` first"}

    h1 = evaluate_h1(results, margin=h1_margin, seed=seed)
    h2 = evaluate_h2(results, band=h2_band, seed=seed)
    holm = holm_bonferroni([h1["p_perm"], h2["p_perm"]])
    h1["holm"], h2["holm"] = holm[0], holm[1]
    return {
        "n_runs": len(results),
        "arms": sorted({r["arm"] for r in results}),
        "primary_tests": [h1, h2],
        "per_category_recall": per_category_table(results, "recall", seed=seed),
        "per_category_f1": per_category_table(results, "f1", seed=seed),
        "note": ("Two pre-registered primary tests (Holm-Bonferroni). All other "
                 "categories/metrics are exploratory/descriptive (docs/week1/08): "
                 "report with effect sizes + CIs, not family-wise significance."),
    }


def print_report(report):
    if report.get("error"):
        print(report["error"])
        return
    print(f"\n=== CloudKC-Bench results  ({report['n_runs']} runs, arms {report['arms']}) ===\n")
    for h in report["primary_tests"]:
        print(f"[{h['hypothesis']}] {h['test']}")
        print(f"    mean diff = {h['mean_diff']:+.4f}  95% CI {h['ci95']}  "
              f"dz = {h['cohens_dz']}  p(perm) = {h['p_perm']}")
        print(f"    Holm-corrected reject H0: {h['holm']['reject']} "
              f"(threshold {h['holm']['adj_threshold']})")
        print(f"    >>> {h['verdict']}: {h['interpretation']}\n")
    print("Per-category recall (mean [95% CI], exploratory):")
    for r in report["per_category_recall"]:
        print(f"    {r['arm']:<3} {r['category']:<24} "
              f"{r['mean']:.3f} [{r['ci95_low']:.3f}, {r['ci95_high']:.3f}]  n={r['n_scenarios']}")
    print(f"\n{report['note']}")


def to_csv(rows, path):
    import csv
    if not rows:
        return path
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path
