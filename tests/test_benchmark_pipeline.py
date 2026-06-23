"""End-to-end P2 pipeline test: generate -> ingest -> seal held-out -> clock model.

Mirrors the P2 Definition of Done: `run_scenarios.sh all` brings up the full
benchmark in a fresh SQLite cache with sealed held-out set.
"""
import os
import pytest

from benchmark import runner, heldout, state_cache, clock_model
from benchmark.simulator.specs import SCENARIO_SPECS
from benchmark.simulator.builder import build_scenario


@pytest.fixture
def workspace(tmp_path):
    db = str(tmp_path / "bench.db")
    manifests = str(tmp_path / "manifests")
    return db, manifests


class TestGenerateAndIngest:
    def test_generate_dev_set(self, workspace):
        db, manifests = workspace
        res = runner.generate("dev", db_path=db, manifests_dir=manifests)
        assert len(res) == 59
        # every dev manifest written to disk
        for sid, info in res.items():
            assert os.path.exists(info["manifest"])
            assert info["events"] > 0

    def test_events_ingested_per_category(self, workspace):
        db, manifests = workspace
        runner.generate("all", db_path=db, manifests_dir=manifests)
        conn = state_cache.connect(db)
        rows = {r["category"]: r for r in state_cache.scenario_summary(conn)}
        conn.close()
        assert rows["multi_stage_kill_chain"]["n_scenarios"] == 18   # 15 KC + HO-01/06/07 multi
        assert rows["benign"]["n_ground_truth"] in (0, None)         # benign has no GT events
        assert rows["single_domain"]["n_events"] > 0


class TestHeldoutSealing:
    def test_seal_and_verify(self, workspace):
        db, manifests = workspace
        runner.generate("all", db_path=db, manifests_dir=manifests)
        heldout_dir = os.path.join(manifests, "heldout")
        lock = heldout.seal(heldout_dir)
        assert lock["n_manifests"] == 10
        ok, mism = heldout.verify(heldout_dir)
        assert ok and mism == []

    def test_tamper_detected(self, workspace):
        db, manifests = workspace
        runner.generate("all", db_path=db, manifests_dir=manifests)
        heldout_dir = os.path.join(manifests, "heldout")
        heldout.seal(heldout_dir)
        # tamper with a sealed manifest
        victim = os.path.join(heldout_dir, "HO-02.json")
        with open(victim, "a") as fh:
            fh.write("\n")
        ok, mism = heldout.verify(heldout_dir)
        assert not ok and any("HO-02" in m for m in mism)


class TestClockModel:
    def test_synthetic_clock_stats(self):
        pairs = []
        for sid in ["KC-02", "SD-06", "EP-01"]:
            events, _ = build_scenario(sid, SCENARIO_SPECS[sid])
            pairs.extend(clock_model.synthetic_pairs(events))
        stats = clock_model.summarize(pairs)
        assert "CloudTrail" in stats["per_source"]
        # CloudTrail modelled lag must exceed EC2 (real-AWS-like skew)
        assert stats["per_source"]["CloudTrail"]["median"] > stats["per_source"]["EC2"]["median"]
