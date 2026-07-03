"""P4/P5 failure-mode analysis (contribution C4, docs/week1/13).

Turns a completed run into the "when and why does it fail" breakdown that
differentiates a journal paper from a workshop one:
  - per-ATT&CK-technique miss rate (which TTPs are consistently not recovered)
  - false-positive characterisation (which spurious TTP@source, and FPs on benign)
  - hardest scenarios per category (lowest mean recall)
  - pre-filter recall stress on low-and-slow (ground-truth evidence dropped before
    any arm sees it)

Works on any completed run (deterministic/Ollama/Gemini); reads scores +
reconstructed_stages + events + manifests. Re-applies the mechanical matching
function at stage granularity to attribute each miss/FP to a technique.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict

from benchmark import state_cache, matching
from benchmark.manifest import Manifest
from benchmark.arms import prefilter
from benchmark.arms.base import ArmEvent

LOW_AND_SLOW = "low_and_slow"


def _reconstruction(conn, run_id):
    rows = conn.execute(
        "SELECT stage_id, ttp_id, telemetry_source, evidence_event_ids, t_start, t_end "
        "FROM reconstructed_stages WHERE run_id=? ORDER BY stage_id", (run_id,)).fetchall()
    return [{"stage_id": r["stage_id"], "ttp_id": r["ttp_id"],
             "telemetry_source": r["telemetry_source"],
             "evidence_event_ids": json.loads(r["evidence_event_ids"]),
             "timestamp_range": [r["t_start"], r["t_end"]]} for r in rows]


def _prefilter_stress(conn, environment):
    """Per low-and-slow scenario: fraction of ground-truth events surviving the
    pre-filter (the recall cost of filtering, docs/week1/13)."""
    where = "AND environment=?" if environment else ""
    args = (LOW_AND_SLOW,) + ((environment,) if environment else ())
    scen = conn.execute(
        "SELECT DISTINCT e.scenario_id FROM events e JOIN scenarios s "
        f"ON s.scenario_id=e.scenario_id WHERE s.category=? {where}", args).fetchall()
    out = {}
    for row in scen:
        sid = row["scenario_id"]
        evrows = conn.execute(
            "SELECT event_id, source, event_time, raw_json, is_ground_truth "
            "FROM events WHERE scenario_id=?", (sid,)).fetchall()
        gt = {r["event_id"] for r in evrows if r["is_ground_truth"]}
        if not gt:
            continue
        arm_events = [ArmEvent.from_row(r) for r in evrows]
        kept = {e.event_id for e in prefilter.apply(arm_events)[0]}
        out[sid] = {"gt_events": len(gt), "gt_kept": len(gt & kept),
                    "prefilter_recall": round(len(gt & kept) / len(gt), 4)}
    return out


def analyze(db_path, environment=None):
    conn = state_cache.connect(db_path)
    where = "WHERE r.environment=?" if environment else ""
    args = (environment,) if environment else ()
    runs = conn.execute(
        "SELECT r.run_id, r.arm, r.scenario_id, s.category, s.manifest_path "
        f"FROM runs r JOIN scenarios s ON s.scenario_id=r.scenario_id {where}", args).fetchall()
    if not runs:
        conn.close()
        return {"error": "no runs found — run `run-arms` first"}

    man_cache = {}
    fn_ttp = defaultdict(lambda: defaultdict(int))   # arm -> ttp -> missed count
    gt_ttp = defaultdict(lambda: defaultdict(int))   # arm -> ttp -> ground-truth count
    fp_key = defaultdict(lambda: defaultdict(int))   # arm -> "ttp@source" -> FP count
    fp_benign = defaultdict(int)                     # arm -> FP count on benign scenarios
    recall_by = defaultdict(lambda: defaultdict(list))  # category -> scenario -> [recall]

    for r in runs:
        arm, sid, cat = r["arm"], r["scenario_id"], r["category"]
        if sid not in man_cache:
            man_cache[sid] = Manifest.load(r["manifest_path"]).to_dict()
        manifest = man_cache[sid]
        recon = _reconstruction(conn, r["run_id"])
        sc = matching.score({"stages": recon}, manifest)

        gt_stage_ttp = {st["stage_id"]: st["ttp_id"] for st in manifest["stages"]}
        for ttp in gt_stage_ttp.values():
            gt_ttp[arm][ttp] += 1
        for stage_id in sc.missed_gt:
            fn_ttp[arm][gt_stage_ttp[stage_id]] += 1
        for idx in sc.spurious_reported:
            st = recon[idx]
            fp_key[arm][f"{st['ttp_id']}@{st['telemetry_source']}"] += 1
            if cat == "benign":
                fp_benign[arm] += 1
        recall_by[cat][sid].append(sc.recall)

    prefilter_stress = _prefilter_stress(conn, environment)
    conn.close()

    # assemble report
    arms = sorted(gt_ttp)
    miss_rates = {}
    for arm in arms:
        rows = []
        for ttp, total in sorted(gt_ttp[arm].items()):
            missed = fn_ttp[arm].get(ttp, 0)
            rows.append({"ttp_id": ttp, "ground_truth": total, "missed": missed,
                         "miss_rate": round(missed / total, 4) if total else 0.0})
        miss_rates[arm] = sorted(rows, key=lambda x: -x["miss_rate"])

    fp_patterns = {arm: sorted([{"pattern": k, "count": v} for k, v in fp_key[arm].items()],
                               key=lambda x: -x["count"]) for arm in arms}

    hardest = {}
    for cat, scen in recall_by.items():
        means = sorted(((s, round(statistics.mean(v), 4)) for s, v in scen.items()),
                       key=lambda x: x[1])
        hardest[cat] = [{"scenario_id": s, "mean_recall": m} for s, m in means[:5]]

    pf_recalls = [v["prefilter_recall"] for v in prefilter_stress.values()]
    return {
        "arms": arms,
        "miss_rate_by_technique": miss_rates,
        "false_positive_patterns": fp_patterns,
        "false_positives_on_benign": dict(fp_benign),
        "hardest_scenarios_per_category": hardest,
        "prefilter_stress_low_and_slow": {
            "per_scenario": prefilter_stress,
            "mean_prefilter_recall": round(statistics.mean(pf_recalls), 4) if pf_recalls else None,
        },
    }


def print_report(rep):
    if rep.get("error"):
        print(rep["error"])
        return
    print("\n=== Failure-mode analysis (C4) ===\n")
    for arm in rep["arms"]:
        top = [r for r in rep["miss_rate_by_technique"][arm] if r["missed"]][:5]
        print(f"[{arm}] most-missed techniques:")
        if not top:
            print("    (none missed)")
        for r in top:
            print(f"    {r['ttp_id']:<11} miss {r['miss_rate']:.0%}  ({r['missed']}/{r['ground_truth']})")
        fb = rep["false_positives_on_benign"].get(arm, 0)
        fps = rep["false_positive_patterns"][arm][:3]
        print(f"    FPs on benign: {fb}; top FP patterns: "
              + (", ".join(f"{p['pattern']}({p['count']})" for p in fps) or "none"))
    print("\nHardest scenarios per category (lowest mean recall):")
    for cat, rows in sorted(rep["hardest_scenarios_per_category"].items()):
        worst = rows[0] if rows else None
        if worst:
            print(f"    {cat:<24} {worst['scenario_id']} (recall {worst['mean_recall']})")
    pf = rep["prefilter_stress_low_and_slow"]
    print(f"\nPre-filter recall on low-and-slow (mean): {pf['mean_prefilter_recall']}")


def to_csv(rep, path):
    import csv
    rows = []
    for arm, techs in rep.get("miss_rate_by_technique", {}).items():
        for t in techs:
            rows.append({"arm": arm, **t})
    if rows:
        with open(path, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    return path
