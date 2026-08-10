#!/usr/bin/env python3
"""Generate ALL paper tables + figures from the run CSVs (matched 7B vs 32B, real-AWS).

Data sources (real-AWS, identical telemetry):
  32B: real_results.csv, detection_realaws.csv, analyze_realaws.csv, confusion_realaws.csv
  7B : paper/data/{results,detection,analyze,confusion}_7b_realaws.csv
Outputs: paper/tables/*.csv  and  paper/figures/*.pdf (+ png/ previews)
"""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.abspath(__file__))
TAB = os.path.join(ROOT, "paper/tables"); os.makedirs(TAB, exist_ok=True)
FIG = os.path.join(ROOT, "paper/figures"); os.makedirs(FIG, exist_ok=True)
PNG = os.path.join(FIG, "png"); os.makedirs(PNG, exist_ok=True)

ARMS = ["A1", "A2", "A3", "A4"]
CATS = ["multi_stage_kill_chain", "low_and_slow", "ephemeral", "single_domain", "benign"]
CATLBL = {"multi_stage_kill_chain": "multi-stage", "low_and_slow": "low-and-slow",
          "ephemeral": "ephemeral", "single_domain": "single-domain", "benign": "benign"}
MS = "multi_stage_kill_chain"
ARM_COLOR = {"A1": "#4f46e5", "A2": "#7c8cf8", "A3": "#a5b4fc", "A4": "#16a34a", "SIGMA": "#86efac"}
C7, C32 = "#a5b4fc", "#3730a3"   # 7B light, 32B dark


def rd(path):
    with open(os.path.join(ROOT, path), newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            try: r[k] = float(v)
            except (TypeError, ValueError): pass
    return rows

def idx(rows, *keys):
    return {tuple(r[k] for k in keys): r for r in rows}

# 32B real-AWS
R32 = idx(rd("real_results.csv"), "arm", "category")
D32 = idx(rd("detection_realaws.csv"), "arm", "category")
A32 = idx(rd("analyze_realaws.csv"), "arm", "category")
CF32 = idx(rd("confusion_realaws.csv"), "arm", "true_ttp")
# 7B real-AWS (matched telemetry)
R7 = idx(rd("paper/data/results_7b_realaws.csv"), "arm", "category")
D7 = idx(rd("paper/data/detection_7b_realaws.csv"), "arm", "category")
A7 = idx(rd("paper/data/analyze_7b_realaws.csv"), "arm", "category")
CF7 = idx(rd("paper/data/confusion_7b_realaws.csv"), "arm", "true_ttp")

SIGMA = {"benign": (1.0, 0.0, 0.0), "ephemeral": (0.5, 0.1333, 0.21),
         "low_and_slow": (0.875, 0.2361, 0.3694), MS: (0.7389, 0.4328, 0.5444),
         "single_domain": (0.75, 0.1944, 0.3083)}

def w(name, header, rows):
    with open(os.path.join(TAB, name), "w", newline="") as fh:
        wr = csv.writer(fh); wr.writerow(header); wr.writerows(rows)
    print("table :", name)

def rn(x, n=3):
    return round(float(x), n) if x not in ("", None) else ""

# ============================================================ TABLES
# T1 two-lens multi-stage (32B) + SIGMA
rows = []
for a in ARMS:
    t, d = R32[(a, MS)], D32[(a, MS)]
    rows.append([a, rn(t["recall"]), rn(t["precision"]), rn(t["f1"]),
                 rn(d["event_recall"]), rn(d["event_precision"]), rn(t["token_cost"], 0), rn(t["latency_ms"], 0)])
s = SIGMA[MS]; rows.append(["SIGMA", rn(s[0]), rn(s[1]), rn(s[2]), "", "", 0, 0])
w("tab1_twolens_multistage.csv",
  ["arm", "tech_recall", "tech_precision", "tech_f1", "event_recall", "event_precision", "tokens", "latency_ms"], rows)

# T2 per-category technique recall + CI (32B) + SIGMA
rows = []
for a in ARMS:
    for c in CATS:
        x = A32[(a, c)]; rows.append([a, CATLBL[c], rn(x["mean"]), rn(x["ci95_low"]), rn(x["ci95_high"])])
for c in CATS: rows.append(["SIGMA", CATLBL[c], rn(SIGMA[c][0]), "", ""])
w("tab2_percategory_technique_recall.csv", ["arm", "category", "recall", "ci95_low", "ci95_high"], rows)

# T3 per-category event (32B)
rows = [[a, CATLBL[c], rn(D32[(a, c)]["event_recall"]), rn(D32[(a, c)]["event_precision"])] for a in ARMS for c in CATS]
w("tab3_percategory_event.csv", ["arm", "category", "event_recall", "event_precision"], rows)

# T4 cost & latency (32B)
rows = [[a, CATLBL[c], rn(R32[(a, c)]["token_cost"], 0), rn(R32[(a, c)]["latency_ms"], 0),
         rn(R32[(a, c)]["filtering_ratio"]), rn(R32[(a, c)]["prefilter_recall"])] for a in ARMS for c in CATS]
w("tab4_cost_latency.csv", ["arm", "category", "tokens", "latency_ms", "filtering_ratio", "prefilter_recall"], rows)

# T5 MODEL SCALE multi-stage: 7B-real vs 32B-real (technique + event)
rows = []
for a in ARMS:
    rows.append([a, rn(R7[(a, MS)]["recall"]), rn(R32[(a, MS)]["recall"]),
                 rn(R7[(a, MS)]["precision"]), rn(R32[(a, MS)]["precision"]),
                 rn(D7[(a, MS)]["event_recall"]), rn(D32[(a, MS)]["event_recall"]),
                 rn(D7[(a, MS)]["event_precision"]), rn(D32[(a, MS)]["event_precision"])])
w("tab5_model_scale_multistage.csv",
  ["arm", "tech_recall_7B", "tech_recall_32B", "tech_prec_7B", "tech_prec_32B",
   "event_recall_7B", "event_recall_32B", "event_prec_7B", "event_prec_32B"], rows)

# T6 MODEL SCALE per-category technique recall: 7B vs 32B
rows = [[a, CATLBL[c], rn(A7[(a, c)]["mean"]), rn(A32[(a, c)]["mean"])] for a in ARMS for c in CATS]
w("tab6_model_scale_percategory_recall.csv", ["arm", "category", "recall_7B", "recall_32B"], rows)

# T7 confusion A1 (32B)
w("tab7_confusion_A1.csv", ["true_ttp", "n", "exact_pct", "parent_pct", "not_detected_pct", "top_wrong"],
  [[t, int(CF32[("A1", t)]["n"]), CF32[("A1", t)]["exact_pct"], CF32[("A1", t)]["parent_pct"],
    CF32[("A1", t)]["not_detected_pct"], CF32[("A1", t)]["top_wrong"]] for (a, t) in CF32 if a == "A1"])

# T8 hypotheses (32B)
w("tab8_hypotheses.csv",
  ["hypothesis", "comparison", "metric", "mean_diff", "ci95_low", "ci95_high", "cohens_dz", "p_perm", "holm_reject", "verdict"],
  [["H1", "A1 vs A4", "technique recall", -0.750, -0.841, -0.654, -3.909, 0.0001, "True", "NOT SUPPORTED"],
   ["H2", "A1 vs A2", "F1", 0.027, -0.051, 0.118, 0.157, 0.587, "False", "FAIL TO REJECT"]])

# T9 confusion scale A1: 7B vs 32B exact/parent per technique
ttps = sorted({t for (a, t) in CF32 if a == "A1"})
rows = [[t, CF7[("A1", t)]["exact_pct"] if ("A1", t) in CF7 else "", CF32[("A1", t)]["exact_pct"],
         CF7[("A1", t)]["parent_pct"] if ("A1", t) in CF7 else "", CF32[("A1", t)]["parent_pct"]] for t in ttps]
w("tab9_confusion_scale_A1.csv", ["true_ttp", "exact_7B", "exact_32B", "parent_7B", "parent_32B"], rows)

# ============================================================ FIGURES
def save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, name), bbox_inches="tight")
    fig.savefig(os.path.join(PNG, name.replace(".pdf", ".png")), dpi=150, bbox_inches="tight")
    plt.close(fig); print("figure:", name)

# 1 two_lens (32B)
fig, ax = plt.subplots(figsize=(6, 3.4)); x = range(len(ARMS)); wd = 0.38
ax.bar([i - wd/2 for i in x], [R32[(a, MS)]["recall"] for a in ARMS], wd, label="technique-level", color="#6366f1")
ax.bar([i + wd/2 for i in x], [D32[(a, MS)]["event_recall"] for a in ARMS], wd, label="event-level", color="#f59e0b")
ax.set_xticks(list(x)); ax.set_xticklabels(ARMS); ax.set_ylabel("recall"); ax.set_ylim(0, 1.05)
ax.set_title("Two scoring lenses — multi-stage (32B, real-AWS)"); ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.3)
save(fig, "two_lens.pdf")

# 2 recall_by_category (32B)
fig, ax = plt.subplots(figsize=(8, 3.6)); x = range(len(CATS)); wd = 0.8/len(ARMS)
for j, a in enumerate(ARMS):
    ax.bar([i + j*wd for i in x], [A32[(a, c)]["mean"] for c in CATS], wd, label=a, color=ARM_COLOR[a])
ax.set_xticks([i + wd*(len(ARMS)-1)/2 for i in x]); ax.set_xticklabels([CATLBL[c] for c in CATS], fontsize=8)
ax.set_ylabel("technique-level recall"); ax.set_ylim(0, 1.05); ax.set_title("Technique-level recall by arm and category (32B, real-AWS)")
ax.legend(frameon=False, ncol=4, fontsize=9); ax.grid(axis="y", alpha=.3); save(fig, "recall_by_category.pdf")

# 3 cost_accuracy (32B)
fig, ax = plt.subplots(figsize=(5.2, 3.6))
for a in ARMS:
    t = R32[(a, MS)]; ax.scatter(t["token_cost"], t["recall"], s=90, color=ARM_COLOR[a], zorder=3)
    ax.annotate(a, (t["token_cost"], t["recall"]), textcoords="offset points", xytext=(6, 4), fontsize=9)
ax.set_xlabel("tokens / scenario"); ax.set_ylabel("technique-level recall"); ax.set_ylim(0, 1.0)
ax.set_title("Cost vs accuracy — multi-stage (32B)"); ax.grid(alpha=.3); save(fig, "cost_accuracy.pdf")

# 4 confusion_A1 (32B) stacked
rows = [CF32[("A1", t)] for (a, t) in CF32 if a == "A1"]; rows.sort(key=lambda r: r["not_detected_pct"])
ttps = [r["true_ttp"] for r in rows]; exact = [r["exact_pct"] for r in rows]
parent = [max(0, r["parent_pct"] - r["exact_pct"]) for r in rows]; missed = [r["not_detected_pct"] for r in rows]
wrong = [max(0, 1 - r["parent_pct"] - r["not_detected_pct"]) for r in rows]
y = range(len(ttps)); fig, ax = plt.subplots(figsize=(6, max(3, .32*len(ttps))))
ax.barh(y, exact, color="#16a34a", label="exact"); ax.barh(y, parent, left=exact, color="#86efac", label="parent-only")
ax.barh(y, wrong, left=[e+p for e, p in zip(exact, parent)], color="#f59e0b", label="wrong technique")
ax.barh(y, missed, left=[e+p+w for e, p, w in zip(exact, parent, wrong)], color="#cbd5e1", label="not detected")
ax.set_yticks(list(y)); ax.set_yticklabels(ttps, fontsize=8); ax.set_xlabel("fraction of ground-truth events"); ax.set_xlim(0, 1)
ax.set_title("Technique attribution — A1 (32B, real-AWS)"); ax.legend(frameon=False, ncol=4, fontsize=8, loc="lower center", bbox_to_anchor=(0.5, 1.02)); save(fig, "confusion_A1.pdf")

# 5 event precision vs recall scatter (32B, multi-stage)
fig, ax = plt.subplots(figsize=(5.2, 4.0))
for a in ARMS:
    d = D32[(a, MS)]; ax.scatter(d["event_recall"], d["event_precision"], s=120, color=ARM_COLOR[a], zorder=3)
    ax.annotate(a, (d["event_recall"], d["event_precision"]), textcoords="offset points", xytext=(7, 5), fontsize=10)
ax.set_xlabel("event-level recall"); ax.set_ylabel("event-level precision"); ax.set_xlim(0.6, 1.02); ax.set_ylim(0.5, 1.05)
ax.set_title("Event-level: LLM more precise than rules (multi-stage, 32B)"); ax.grid(alpha=.3); save(fig, "event_precision_recall.pdf")

# 6 per-category event recall by arm (32B)
fig, ax = plt.subplots(figsize=(7.6, 3.6)); x = range(len(CATS)); wd = 0.8/len(ARMS)
for j, a in enumerate(ARMS):
    ax.bar([i + j*wd for i in x], [D32[(a, c)]["event_recall"] if D32[(a, c)]["event_recall"] != "" else 0 for c in CATS], wd, label=a, color=ARM_COLOR[a])
ax.set_xticks([i + wd*(len(ARMS)-1)/2 for i in x]); ax.set_xticklabels([CATLBL[c] for c in CATS], fontsize=8)
ax.set_ylabel("event-level recall"); ax.set_ylim(0, 1.05); ax.set_title("Event-level recall by arm and category (32B, real-AWS)")
ax.legend(frameon=False, ncol=4, fontsize=9); ax.grid(axis="y", alpha=.3); save(fig, "percategory_event.pdf")

# 7 MODEL SCALE multi-stage technique recall: 7B vs 32B (matched)
fig, ax = plt.subplots(figsize=(6, 3.6)); x = range(len(ARMS)); wd = 0.38
b7 = ax.bar([i - wd/2 for i in x], [R7[(a, MS)]["recall"] for a in ARMS], wd, label="7B", color=C7)
b32 = ax.bar([i + wd/2 for i in x], [R32[(a, MS)]["recall"] for a in ARMS], wd, label="32B", color=C32)
for bars in (b7, b32):
    for b in bars: ax.annotate(f"{b.get_height():.2f}", (b.get_x()+b.get_width()/2, b.get_height()), textcoords="offset points", xytext=(0, 2), ha="center", fontsize=6.5)
ax.set_xticks(list(x)); ax.set_xticklabels(ARMS); ax.set_ylabel("technique-level recall"); ax.set_ylim(0, 1.0)
ax.set_title("Model scale on identical real-AWS telemetry: 7B vs 32B"); ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.3)
save(fig, "fig_model_scale_multistage.pdf")

# 8 MODEL SCALE event-level: 7B vs 32B (recall & precision, multi-stage)
fig, ax = plt.subplots(figsize=(6.2, 3.6)); x = range(len(ARMS)); wd = 0.2
ax.bar([i - 1.5*wd for i in x], [D7[(a, MS)]["event_recall"] for a in ARMS], wd, label="7B recall", color=C7)
ax.bar([i - 0.5*wd for i in x], [D32[(a, MS)]["event_recall"] for a in ARMS], wd, label="32B recall", color=C32)
ax.bar([i + 0.5*wd for i in x], [D7[(a, MS)]["event_precision"] for a in ARMS], wd, label="7B precision", color="#fcd34d")
ax.bar([i + 1.5*wd for i in x], [D32[(a, MS)]["event_precision"] for a in ARMS], wd, label="32B precision", color="#d97706")
ax.set_xticks(list(x)); ax.set_xticklabels(ARMS); ax.set_ylim(0, 1.1); ax.set_ylabel("event-level")
ax.set_title("Event-level is scale-robust: 7B vs 32B (multi-stage)"); ax.legend(frameon=False, fontsize=7.5, ncol=2); ax.grid(axis="y", alpha=.3)
save(fig, "fig_model_scale_event.pdf")

# 9 MODEL SCALE per-category technique recall (A1): 7B vs 32B
fig, ax = plt.subplots(figsize=(6.8, 3.4)); x = range(len(CATS)); wd = 0.38
ax.bar([i - wd/2 for i in x], [A7[("A1", c)]["mean"] for c in CATS], wd, label="7B", color=C7)
ax.bar([i + wd/2 for i in x], [A32[("A1", c)]["mean"] for c in CATS], wd, label="32B", color=C32)
ax.set_xticks(list(x)); ax.set_xticklabels([CATLBL[c] for c in CATS], fontsize=8)
ax.set_ylabel("technique-level recall (A1)"); ax.set_ylim(0, 0.5); ax.set_title("Model scale by category (A1): 7B vs 32B")
ax.legend(frameon=False, fontsize=9); ax.grid(axis="y", alpha=.3); save(fig, "fig_model_scale_percategory.pdf")

# 10 confusion scale A1: 7B vs 32B exact-attribution per technique
ttps2 = sorted([t for (a, t) in CF32 if a == "A1"], key=lambda t: CF32[("A1", t)]["exact_pct"])
e7 = [CF7[("A1", t)]["exact_pct"] if ("A1", t) in CF7 else 0 for t in ttps2]
e32 = [CF32[("A1", t)]["exact_pct"] for t in ttps2]
y = range(len(ttps2)); h = 0.38
fig, ax = plt.subplots(figsize=(6, max(3.5, .34*len(ttps2))))
ax.barh([i - h/2 for i in y], e7, h, label="7B", color=C7); ax.barh([i + h/2 for i in y], e32, h, label="32B", color=C32)
ax.set_yticks(list(y)); ax.set_yticklabels(ttps2, fontsize=8); ax.set_xlabel("exact-attribution rate"); ax.set_xlim(0, 1.05)
ax.set_title("Does scale fix attribution? Exact rate per technique (A1)"); ax.legend(frameon=False, fontsize=9); ax.grid(axis="x", alpha=.3)
save(fig, "fig_confusion_scale_A1.pdf")

print("\nDONE - 9 tables, 10 figures")
