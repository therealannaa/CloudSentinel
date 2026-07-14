"""Per-category analysis of experiment results — the P3-ready aggregation.

Honors the frozen protocol (docs/week1/01, docs/week1/08):
  - unit of analysis = scenario: average seeds -> scenario first, then categories
  - NEVER pool the five categories
Full effect-sizes / bootstrap CIs / Holm-Bonferroni are P4; this provides the
per-(arm, category) point estimates + the C3 cost/latency table the runner feeds.
"""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict


def _mean(xs):
    return round(statistics.mean(xs), 4) if xs else 0.0


def per_category(results):
    """results: list of per-run dicts from experiment.run_experiment.
    Returns rows of {arm, category, recall, precision, f1, ...} where each metric is
    the mean over scenarios of the per-scenario (seed-averaged) value."""
    # 1. average seeds -> one value per (arm, scenario)
    by_scen = defaultdict(lambda: defaultdict(list))
    cat_of = {}
    # provenance (model_version / environment) is constant per run set; carry it so the
    # exported CSV is self-describing and can't be mistaken for another model/env's run
    provenance = {}
    for r in results:
        key = (r["arm"], r["scenario_id"])
        cat_of[r["scenario_id"]] = r["category"]
        if "model_version" in r:
            provenance["model_version"] = r["model_version"]
        if "environment" in r:
            provenance["environment"] = r["environment"]
        for m in ("recall", "precision", "f1", "token_cost", "latency_ms",
                  "prefilter_in", "prefilter_out", "prefilter_recall"):
            by_scen[key][m].append(r[m])
    scen_level = {k: {m: _mean(v) for m, v in d.items()} for k, d in by_scen.items()}

    # 2. average scenarios -> one value per (arm, category)
    by_cat = defaultdict(lambda: defaultdict(list))
    for (arm, sid), metrics in scen_level.items():
        cat = cat_of[sid]
        for m, v in metrics.items():
            by_cat[(arm, cat)][m].append(v)

    rows = []
    for (arm, cat), metrics in sorted(by_cat.items()):
        row = {"arm": arm, "category": cat,
               "model_version": provenance.get("model_version", ""),
               "environment": provenance.get("environment", ""),
               "n_scenarios": len(metrics["recall"])}
        for m, vals in metrics.items():
            row[m] = _mean(vals)
        # filtering ratio = out/in (C3)
        row["filtering_ratio"] = round(row["prefilter_out"] / row["prefilter_in"], 4) \
            if row.get("prefilter_in") else 0.0
        rows.append(row)
    return rows


def print_table(rows):
    cols = ["arm", "category", "model_version", "environment", "n_scenarios",
            "recall", "precision", "f1",
            "filtering_ratio", "prefilter_recall", "token_cost", "latency_ms"]
    print("  ".join(c[:14].ljust(14) for c in cols))
    for r in rows:
        print("  ".join(str(r.get(c, "")).ljust(14) for c in cols))


def to_csv(rows, path):
    if not rows:
        return path
    cols = list(rows[0].keys())
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path
