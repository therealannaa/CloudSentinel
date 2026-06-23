"""Benchmark generator runner — produces manifests + ingests telemetry into the
SQLite state cache for a scenario set (dev / heldout / all).

This is the `./run_scenarios.sh dev` entry point of the P2 Definition of Done:
simulator fires -> telemetry captured -> manifest produced -> all validated.
"""
from __future__ import annotations

import os

from benchmark import state_cache
from benchmark.simulator.specs import SCENARIO_SPECS, dev_ids, heldout_ids, all_ids
from benchmark.simulator.builder import build_scenario


def _ids_for(scenario_set):
    return {"dev": dev_ids, "heldout": heldout_ids, "all": all_ids}[scenario_set]()


def generate(scenario_set="dev", db_path="cloudsentinel.db",
             manifests_dir="benchmark/manifests", environment="synthetic",
             author="Atishay"):
    """Generate one scenario set end-to-end.

    Returns a summary dict: per scenario the #events, #ground-truth events, and
    manifest validation result. Raises if any manifest is invalid.
    """
    os.makedirs(manifests_dir, exist_ok=True)
    conn = state_cache.init_state_cache(db_path)

    results = {}
    for sid in _ids_for(scenario_set):
        spec = SCENARIO_SPECS[sid]
        events, manifest = build_scenario(sid, spec, author=author)
        for e in events:
            e.environment = environment

        errors = manifest.validate()
        if errors:
            raise ValueError(f"{sid}: invalid manifest: {errors}")

        # held-out manifests are written to a separate dir so they can be sealed
        sub = "heldout" if spec["held_out"] else "dev"
        out_dir = os.path.join(manifests_dir, sub)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{sid}.json")
        manifest.save(path)

        state_cache.upsert_scenario(
            conn, sid, spec["category"], is_held_out=spec["held_out"],
            manifest_path=path, author=author,
            reviewer=manifest.authorship.get("reviewer") or None,
        )
        state_cache.insert_events(conn, events)

        gt = sum(1 for e in events if e.is_ground_truth)
        results[sid] = {"events": len(events), "ground_truth": gt,
                        "stages": len(manifest.stages), "manifest": path,
                        "held_out": spec["held_out"]}

    conn.close()
    return results


def summary_table(db_path="cloudsentinel.db"):
    conn = state_cache.connect(db_path)
    rows = state_cache.scenario_summary(conn)
    conn.close()
    return rows
