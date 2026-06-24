"""Benchmark runner — runs arms A1-A4 over a scenario set across seeds, scores each
reconstruction with the mechanical matching function, and writes runs / stages /
scores to the SQLite state cache. This is the P3 `benchmark_runner`.

Honors the frozen protocol: scenario = unit of analysis, seeds = repeated measures,
arms held fixed except the variable under test. Records C3 inputs (filtering ratio,
pre-filter recall, token cost, latency) per run.
"""
from __future__ import annotations

import json
import os

from benchmark import state_cache, matching, runner as gen_runner
from benchmark.manifest import Manifest
from benchmark.arms import get_arm, ARMS
from benchmark.arms.base import ArmEvent
from benchmark.arms import prefilter
from benchmark.arms.llm_client import get_client


def _load_arm_events(conn, scenario_id):
    rows = conn.execute(
        """SELECT event_id, source, event_time, raw_json FROM events
           WHERE scenario_id=? ORDER BY event_time, event_id""", (scenario_id,)
    ).fetchall()
    return [ArmEvent.from_row(r) for r in rows]


def _ground_truth_ids(conn, scenario_id):
    rows = conn.execute(
        "SELECT event_id FROM events WHERE scenario_id=? AND is_ground_truth=1",
        (scenario_id,)).fetchall()
    return {r["event_id"] for r in rows}


def _write_reconstruction(conn, run_id, chain):
    conn.execute("DELETE FROM reconstructed_stages WHERE run_id=?", (run_id,))
    for s in chain.get("stages", []):
        tr = s.get("timestamp_range", [None, None])
        conn.execute(
            """INSERT INTO reconstructed_stages
                   (run_id, stage_id, ttp_id, telemetry_source, evidence_event_ids, t_start, t_end)
               VALUES (?,?,?,?,?,?,?)""",
            (run_id, s["stage_id"], s["ttp_id"], s["telemetry_source"],
             json.dumps(s["evidence_event_ids"]), tr[0], tr[1]))
    conn.commit()


def run_experiment(arms=ARMS, scenario_set="dev", seeds=3,
                   db_path="cloudsentinel.db", manifests_dir="benchmark/manifests",
                   environment="synthetic", model_version=None, auto_generate=True,
                   limit=None):
    """Run the ablation. Returns a list of per-run result dicts.

    If the scenario set hasn't been generated into the cache yet, generates it
    first (auto_generate). The shared LLM client is created once and reused.
    """
    conn = state_cache.connect(db_path)
    have = conn.execute("SELECT COUNT(*) FROM scenarios").fetchone()[0] if \
        conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scenarios'").fetchone() else 0
    if auto_generate and not have:
        conn.close()
        gen_runner.generate(scenario_set if scenario_set != "all" else "all",
                            db_path=db_path, manifests_dir=manifests_dir, environment=environment)
        conn = state_cache.connect(db_path)

    client = get_client()
    model_version = model_version or (
        os.getenv("GEMINI_MODEL", "gemini-2.0-flash") if client.name == "gemini"
        else "deterministic-v1")
    arm_objs = {code: get_arm(code, client=client) for code in arms}

    where = {"dev": "WHERE is_held_out=0", "heldout": "WHERE is_held_out=1", "all": ""}[scenario_set]
    scen_rows = conn.execute(
        f"SELECT scenario_id, category, manifest_path FROM scenarios {where} ORDER BY scenario_id"
    ).fetchall()
    if limit:
        scen_rows = scen_rows[:limit]   # cheap smoke test (esp. for paid LLM runs)

    results = []
    for sr in scen_rows:
        sid = sr["scenario_id"]
        events = _load_arm_events(conn, sid)
        gt_ids = _ground_truth_ids(conn, sid)
        manifest = Manifest.load(sr["manifest_path"]).to_dict()

        # pre-filter recall is a per-scenario measured result (shared, deterministic)
        kept_ids = {e.event_id for e in prefilter.apply(events)[0]}
        pf_recall = (len(kept_ids & gt_ids) / len(gt_ids)) if gt_ids else 1.0

        for code in arms:
            arm = arm_objs[code]
            for seed in range(seeds):
                res = arm.run(events, seed=seed)
                sc = matching.score(res.reconstructed, manifest)
                run_id = f"{code}-{sid}-{seed}-{environment}"
                state_cache.insert_run(
                    conn, run_id, code, environment, sid, seed,
                    model_version=model_version, latency_ms=res.latency_ms,
                    token_cost=res.token_cost,
                    prefilter_events_in=res.prefilter_events_in,
                    prefilter_events_out=res.prefilter_events_out)
                _write_reconstruction(conn, run_id, res.reconstructed)
                state_cache.insert_score(conn, run_id, sc)
                results.append({
                    "run_id": run_id, "arm": code, "scenario_id": sid,
                    "category": sr["category"], "seed": seed,
                    "recall": sc.recall, "precision": sc.precision, "f1": sc.f1,
                    "tp": sc.tp, "fp": sc.fp, "fn": sc.fn,
                    "token_cost": res.token_cost, "latency_ms": res.latency_ms,
                    "prefilter_in": res.prefilter_events_in,
                    "prefilter_out": res.prefilter_events_out,
                    "prefilter_recall": round(pf_recall, 4),
                })
    conn.close()
    return results
