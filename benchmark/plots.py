"""Figure generation for the paper/deliverables.

Turns the CSVs emitted by the CLI into publication figures. Environment-agnostic:
run it on the real-AWS results CSVs for the headline figures, and on LocalStack for
the reproducibility-layer panel.

Inputs (all optional; a figure is skipped if its CSV is missing):
  --results     from `run-arms --csv`      (technique-level recall/precision/cost per category)
  --detection   from `detection --csv`     (event-level recall/precision per category)
  --confusion   from `confusion --csv`     (per-true-technique exact/parent/missed)

Usage:
  pip install matplotlib
  python -m benchmark.plots --results results.csv --detection det.csv \
         --confusion conf.csv --category multi_stage_kill_chain --outdir paper/figures
"""
from __future__ import annotations

import argparse
import csv
import os

# consistent arm colours (LLM arms warm/indigo family, rules arms green family)
ARM_COLOR = {"A1": "#4f46e5", "A2": "#7c8cf8", "A3": "#a5b4fc",
             "A4": "#16a34a", "SIGMA": "#86efac"}
ARM_ORDER = ["A1", "A2", "A3", "A4", "SIGMA"]


def _read(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            try:
                r[k] = float(v)
            except (TypeError, ValueError):
                pass
    return rows


def _arms(rows):
    return [a for a in ARM_ORDER if any(r["arm"] == a for r in rows)]


def fig_two_lens(results, detection, category, out):
    """Grouped bars: technique-level vs event-level recall per arm (the headline)."""
    import matplotlib.pyplot as plt
    tech = {r["arm"]: r["recall"] for r in results if r["category"] == category}
    ev = {r["arm"]: r["event_recall"] for r in detection if r["category"] == category}
    arms = [a for a in ARM_ORDER if a in tech]
    x = range(len(arms)); w = 0.38
    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.bar([i - w/2 for i in x], [tech.get(a, 0) for a in arms], w,
           label="technique-level", color="#6366f1")
    ax.bar([i + w/2 for i in x], [ev.get(a, 0) for a in arms], w,
           label="event-level", color="#f59e0b")
    ax.set_xticks(list(x)); ax.set_xticklabels(arms)
    ax.set_ylabel("recall"); ax.set_ylim(0, 1.05)
    ax.set_title(f"Two scoring lenses — {category}")
    ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def fig_per_category(results, out):
    """Grouped bars: recall per arm, per category."""
    import matplotlib.pyplot as plt
    cats = sorted({r["category"] for r in results})
    arms = _arms(results)
    val = {(r["arm"], r["category"]): r["recall"] for r in results}
    x = range(len(cats)); w = 0.8 / max(len(arms), 1)
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for j, a in enumerate(arms):
        ax.bar([i + j*w for i in x], [val.get((a, c), 0) for c in cats], w,
               label=a, color=ARM_COLOR.get(a, "#888"))
    ax.set_xticks([i + w*(len(arms)-1)/2 for i in x])
    ax.set_xticklabels([c.replace("_", "\n") for c in cats], fontsize=8)
    ax.set_ylabel("technique-level recall"); ax.set_ylim(0, 1.05)
    ax.set_title("Recall by arm and category")
    ax.legend(frameon=False, ncol=len(arms), fontsize=9); ax.grid(axis="y", alpha=.3)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def fig_cost_accuracy(results, category, out):
    """Scatter: token cost vs recall per arm (C3 efficiency frontier)."""
    import matplotlib.pyplot as plt
    rows = [r for r in results if r["category"] == category]
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    for r in rows:
        ax.scatter(r["token_cost"], r["recall"], s=90,
                   color=ARM_COLOR.get(r["arm"], "#888"), zorder=3)
        ax.annotate(r["arm"], (r["token_cost"], r["recall"]),
                    textcoords="offset points", xytext=(6, 4), fontsize=9)
    ax.set_xlabel("tokens / scenario"); ax.set_ylabel("technique-level recall")
    ax.set_ylim(0, 1.05); ax.set_title(f"Cost vs accuracy — {category}")
    ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def fig_confusion(confusion, out, arm=None):
    """Stacked bars: per true technique, exact / parent-only / missed."""
    import matplotlib.pyplot as plt
    rows = [r for r in confusion if arm is None or r["arm"] == arm]
    rows.sort(key=lambda r: r["not_detected_pct"])
    ttps = [r["true_ttp"] for r in rows]
    exact = [r["exact_pct"] for r in rows]
    parent = [max(0.0, r["parent_pct"] - r["exact_pct"]) for r in rows]
    missed = [r["not_detected_pct"] for r in rows]
    wrong = [max(0.0, 1 - e - p - m) for e, p, m in zip(exact, parent, missed)]
    y = range(len(ttps))
    fig, ax = plt.subplots(figsize=(6, max(3, 0.32*len(ttps))))
    ax.barh(y, exact, color="#16a34a", label="exact")
    ax.barh(y, parent, left=exact, color="#86efac", label="parent-only")
    ax.barh(y, wrong, left=[e+p for e, p in zip(exact, parent)], color="#f59e0b", label="wrong technique")
    ax.barh(y, missed, left=[e+p+w for e, p, w in zip(exact, parent, wrong)], color="#cbd5e1", label="not detected")
    ax.set_yticks(list(y)); ax.set_yticklabels(ttps, fontsize=8)
    ax.set_xlabel("fraction of ground-truth events"); ax.set_xlim(0, 1)
    ax.set_title(f"Technique attribution{' — ' + arm if arm else ''}")
    ax.legend(frameon=False, ncol=4, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.02))
    fig.tight_layout(); fig.savefig(out, bbox_inches="tight"); plt.close(fig)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(prog="benchmark.plots")
    p.add_argument("--results"); p.add_argument("--detection"); p.add_argument("--confusion")
    p.add_argument("--category", default="multi_stage_kill_chain")
    p.add_argument("--arm", default="A1")
    p.add_argument("--outdir", default="paper/figures")
    p.add_argument("--ext", default="pdf", choices=["pdf", "png"])
    a = p.parse_args(argv)
    os.makedirs(a.outdir, exist_ok=True)
    results, detection, confusion = _read(a.results), _read(a.detection), _read(a.confusion)
    made = []
    if results:
        made.append(fig_per_category(results, f"{a.outdir}/recall_by_category.{a.ext}"))
        made.append(fig_cost_accuracy(results, a.category, f"{a.outdir}/cost_accuracy.{a.ext}"))
    if results and detection:
        made.append(fig_two_lens(results, detection, a.category, f"{a.outdir}/two_lens.{a.ext}"))
    if confusion:
        made.append(fig_confusion(confusion, f"{a.outdir}/confusion_{a.arm}.{a.ext}", arm=a.arm))
    if not made:
        print("no input CSVs found — pass --results/--detection/--confusion")
        return 1
    for m in made:
        print("wrote", m)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
