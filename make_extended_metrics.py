#!/usr/bin/env python3
"""Tier-1 extended performance metrics + non-bar figures, from the run DBs.
Event-level confusion (TP/FP/TN/FN) recovered from real.db / real_7b.db, no re-run.
Outputs: paper/tables/tab10_extended_metrics.csv and several paper/figures/*.pdf (+png).
"""
import sqlite3, json, math, os, statistics as st
from collections import defaultdict
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(ROOT, "paper/figures"); PNG = os.path.join(FIG, "png"); TAB = os.path.join(ROOT, "paper/tables")
DB32 = os.path.join(ROOT, "real.db"); DB7 = os.path.join(ROOT, "paper/data/real_7b.db")
ARMS = ["A1", "A2", "A3", "A4"]; MS = "multi_stage_kill_chain"
ARM_COLOR = {"A1": "#4f46e5", "A2": "#7c8cf8", "A3": "#a5b4fc", "A4": "#16a34a"}


def load(db):
    """Return per-run records: arm, scenario, seed, category, event confusion, tech recall, latency, tokens."""
    c = sqlite3.connect(db)
    tot = {r[0]: r[1] for r in c.execute("SELECT scenario_id,COUNT(*) FROM events GROUP BY scenario_id")}
    gt = defaultdict(set)
    for sid, eid in c.execute("SELECT scenario_id,event_id FROM events WHERE is_ground_truth=1"):
        gt[sid].add(eid)
    recs = []
    q = ("SELECT r.run_id,r.arm,r.scenario_id,r.seed,s.category,r.latency_ms,r.token_cost,sc.recall "
         "FROM runs r JOIN scenarios s ON s.scenario_id=r.scenario_id "
         "LEFT JOIN scores sc ON sc.run_id=r.run_id WHERE r.environment='real_aws'")
    for run_id, arm, sid, seed, cat, lat, tok, trec in c.execute(q):
        recon = set()
        for (ev,) in c.execute("SELECT evidence_event_ids FROM reconstructed_stages WHERE run_id=?", (run_id,)):
            recon |= set(json.loads(ev))
        g = gt[sid]; TP = len(recon & g); FP = len(recon) - TP; FN = len(g) - TP; TN = tot[sid] - len(recon | g)
        recs.append(dict(arm=arm, sid=sid, seed=seed, cat=cat, TP=TP, FP=FP, FN=FN, TN=TN,
                         lat=lat or 0, tok=tok or 0, trec=trec if trec is not None else 0.0))
    c.close(); return recs


def metrics(TP, FP, FN, TN):
    rec = TP/(TP+FN) if TP+FN else float('nan')
    prec = TP/(TP+FP) if TP+FP else float('nan')
    f1 = 2*TP/(2*TP+FP+FN) if (2*TP+FP+FN) else float('nan')
    fpr = FP/(FP+TN) if FP+TN else float('nan')
    spec = TN/(TN+FP) if TN+FP else float('nan')
    acc = (TP+TN)/(TP+FP+FN+TN)
    bal = (rec+spec)/2 if rec == rec and spec == spec else float('nan')
    den = math.sqrt((TP+FP)*(TP+FN)*(TN+FP)*(TN+FN))
    mcc = (TP*TN-FP*FN)/den if den else float('nan')
    return dict(ev_recall=rec, ev_prec=prec, ev_f1=f1, fpr=fpr, spec=spec, acc=acc, bal_acc=bal, mcc=mcc)


def arm_metrics(recs, cat=MS):
    """Micro-pooled event metrics per arm for a category, + seed-std of technique recall, latency pctiles, efficiency."""
    out = {}
    for a in ARMS:
        rr = [r for r in recs if r["arm"] == a and r["cat"] == cat]
        TP = sum(r["TP"] for r in rr); FP = sum(r["FP"] for r in rr); FN = sum(r["FN"] for r in rr); TN = sum(r["TN"] for r in rr)
        m = metrics(TP, FP, FN, TN)
        # seed-std: per scenario, std of technique recall across seeds, then mean over scenarios
        byscen = defaultdict(list)
        for r in rr:
            byscen[r["sid"]].append(r["trec"])
        stds = [st.pstdev(v) for v in byscen.values() if len(v) > 1]
        m["seed_std"] = round(sum(stds)/len(stds), 4) if stds else 0.0
        lats = [r["lat"] for r in rr if r["lat"] > 0]
        m["lat_p50"] = round(float(np.percentile(lats, 50)), 0) if lats else 0
        m["lat_p95"] = round(float(np.percentile(lats, 95)), 0) if lats else 0
        toks = [r["tok"] for r in rr if r["tok"] > 0]
        mean_tok = sum(toks)/len(toks) if toks else 0
        m["recall_per_1k_tok"] = round(m["ev_recall"]/(mean_tok/1000), 3) if mean_tok else float('nan')
        m["tech_recall_dist"] = [r["trec"] for r in rr]
        m["lat_dist"] = lats
        out[a] = m
    return out


R32 = load(DB32); R7 = load(DB7)
M32 = arm_metrics(R32); M7 = arm_metrics(R7)

# ---- TABLE ----
def rn(x, n=3):
    return "" if x != x else round(x, n)
with open(os.path.join(TAB, "tab10_extended_metrics.csv"), "w") as fh:
    fh.write("model,arm,event_recall,event_precision,event_f1,fpr,specificity,balanced_accuracy,mcc,accuracy,seed_std,latency_p50_ms,latency_p95_ms,recall_per_1k_tokens\n")
    for tag, M in (("32B", M32), ("7B", M7)):
        for a in ARMS:
            m = M[a]
            fh.write(f"{tag},{a},{rn(m['ev_recall'])},{rn(m['ev_prec'])},{rn(m['ev_f1'])},{rn(m['fpr'])},"
                     f"{rn(m['spec'])},{rn(m['bal_acc'])},{rn(m['mcc'])},{rn(m['acc'])},{m['seed_std']},"
                     f"{int(m['lat_p50'])},{int(m['lat_p95'])},{rn(m['recall_per_1k_tok'])}\n")
print("table : tab10_extended_metrics.csv")

def save(fig, name):
    fig.tight_layout(); fig.savefig(os.path.join(FIG, name), bbox_inches="tight")
    fig.savefig(os.path.join(PNG, name.replace(".pdf", ".png")), dpi=150, bbox_inches="tight"); plt.close(fig)
    print("figure:", name)

# ---- 1. RADAR (arms x 6 metrics, 32B multi-stage) ----
keys = ["ev_f1", "mcc", "bal_acc", "spec", "ev_recall", "ev_prec"]
labels = ["Event F1", "MCC", "Balanced\nAccuracy", "Specificity", "Event\nRecall", "Event\nPrecision"]
ang = np.linspace(0, 2*np.pi, len(keys), endpoint=False).tolist(); ang += ang[:1]
fig = plt.figure(figsize=(5.6, 5.2)); ax = plt.subplot(111, polar=True)
for a in ARMS:
    v = [M32[a][k] for k in keys]; v += v[:1]
    ax.plot(ang, v, color=ARM_COLOR[a], lw=2, label=a); ax.fill(ang, v, color=ARM_COLOR[a], alpha=0.08)
ax.set_xticks(ang[:-1]); ax.set_xticklabels(labels, fontsize=8.5)
ax.set_ylim(0, 1); ax.set_yticks([0.25, 0.5, 0.75, 1.0]); ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=7)
ax.set_title("Multi-metric profile per arm (32B, multi-stage)", fontsize=11, pad=18)
ax.legend(loc="upper right", bbox_to_anchor=(1.22, 1.12), frameon=False, fontsize=9)
save(fig, "fig_metrics_radar.pdf")

# ---- 2. ROC SPACE (FPR vs TPR; 32B solid, 7B hollow) ----
fig, ax = plt.subplots(figsize=(5.4, 5.0))
ax.plot([0, 1], [0, 1], "--", color="#94a3b8", lw=1, label="random")
ax.scatter([0], [1], marker="*", s=220, color="#f59e0b", zorder=4, label="ideal")
for a in ARMS:
    ax.scatter(M32[a]["fpr"], M32[a]["ev_recall"], s=130, color=ARM_COLOR[a], zorder=3)
    ax.annotate(f"{a} (32B)", (M32[a]["fpr"], M32[a]["ev_recall"]), textcoords="offset points", xytext=(8, 4), fontsize=8.5)
    ax.scatter(M7[a]["fpr"], M7[a]["ev_recall"], s=110, facecolors="none", edgecolors=ARM_COLOR[a], lw=1.8, zorder=3)
ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate (event recall)")
ax.set_xlim(-0.03, 1.0); ax.set_ylim(0.5, 1.03)
ax.set_title("ROC space — arms as operating points (multi-stage)\nfilled = 32B, hollow = 7B", fontsize=10)
ax.legend(frameon=False, fontsize=8, loc="lower right"); ax.grid(alpha=.3)
save(fig, "fig_roc_space.pdf")

# ---- 3. SEED-STABILITY BOX PLOT (technique recall dist per arm, 32B multi-stage) ----
fig, ax = plt.subplots(figsize=(6, 3.6))
data = [M32[a]["tech_recall_dist"] for a in ARMS]
bp = ax.boxplot(data, labels=ARMS, patch_artist=True, showmeans=True, widths=0.55)
for patch, a in zip(bp["boxes"], ARMS):
    patch.set_facecolor(ARM_COLOR[a]); patch.set_alpha(0.45)
ax.set_ylabel("technique-level recall (per run)"); ax.set_ylim(-0.03, 1.0)
ax.set_title("Run-to-run stability across scenarios and seeds (32B, multi-stage)", fontsize=10)
ax.grid(axis="y", alpha=.3)
save(fig, "fig_seed_stability_box.pdf")

# ---- 4. METRICS HEATMAP (arms x metrics, 32B multi-stage) ----
hcols = ["ev_recall", "ev_prec", "ev_f1", "mcc", "bal_acc", "spec", "fpr"]
hlab = ["Ev.Rec", "Ev.Prec", "Ev.F1", "MCC", "Bal.Acc", "Spec", "FPR"]
mat = np.array([[M32[a][k] for k in hcols] for a in ARMS])
fig, ax = plt.subplots(figsize=(6.2, 3.2))
im = ax.imshow(mat, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(hlab))); ax.set_xticklabels(hlab, fontsize=8.5)
ax.set_yticks(range(len(ARMS))); ax.set_yticklabels(ARMS, fontsize=9)
for i in range(len(ARMS)):
    for j in range(len(hcols)):
        ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", fontsize=8,
                color="black" if 0.25 < mat[i, j] < 0.85 else "white")
ax.set_title("Event-level metrics heatmap (32B, multi-stage)\n(FPR: lower is better)", fontsize=10)
fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
save(fig, "fig_metrics_heatmap.pdf")

# ---- 5. LATENCY BOX PLOT (per-run latency per LLM arm, 32B multi-stage) ----
fig, ax = plt.subplots(figsize=(5.6, 3.4))
llm = ["A1", "A2", "A3"]
data = [[l/1000 for l in M32[a]["lat_dist"]] for a in llm]
bp = ax.boxplot(data, labels=llm, patch_artist=True, showmeans=True, widths=0.5)
for patch, a in zip(bp["boxes"], llm):
    patch.set_facecolor(ARM_COLOR[a]); patch.set_alpha(0.45)
ax.set_ylabel("latency per scenario (s)")
ax.set_title("Latency distribution per LLM arm (32B, multi-stage)", fontsize=10)
ax.grid(axis="y", alpha=.3)
save(fig, "fig_latency_box.pdf")

print("\nDONE - 1 table, 5 non-bar figures")
