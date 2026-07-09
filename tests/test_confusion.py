"""Tests for agent_outputs capture + technique-attribution confusion (C4)."""
import json
import pytest

from benchmark import experiment, runner as gen_runner, state_cache, failure_analysis


@pytest.fixture
def run_db(tmp_path):
    db = str(tmp_path / "c.db")
    man = str(tmp_path / "m")
    gen_runner.generate("dev", db_path=db, manifests_dir=man)
    experiment.run_experiment(arms=("A4",), scenario_set="dev",
                              category="multi_stage_kill_chain", seeds=1,
                              db_path=db, manifests_dir=man, auto_generate=False)
    return db


class TestAgentOutputCapture:
    def test_agent_outputs_written(self, run_db):
        conn = state_cache.connect(run_db)
        n = conn.execute("SELECT COUNT(*) FROM agent_outputs").fetchone()[0]
        rows = conn.execute("SELECT output_json FROM agent_outputs LIMIT 1").fetchall()
        conn.close()
        assert n == 15                              # 15 KC scenarios x A4 x 1 seed
        cands = json.loads(rows[0]["output_json"])
        assert all({"event_id", "ttp_id", "source"} <= set(c) for c in cands)


class TestConfusion:
    def test_a4_maps_t1580_to_wrong_family(self, run_db):
        # A4 signatures map discovery to T1526, so true T1580 is NEVER exact
        rows = failure_analysis.technique_confusion(run_db, arm="A4")
        by_ttp = {r["true_ttp"]: r for r in rows}
        assert "T1580" in by_ttp
        assert by_ttp["T1580"]["exact_pct"] == 0.0       # never assigned T1580
        # A4 assigns exact for cleanly-mapped techniques (e.g. T1098.001 CreateAccessKey)
        assert by_ttp.get("T1098.001", {}).get("exact_pct", 0) > 0.5

    def test_rows_have_expected_fields(self, run_db):
        rows = failure_analysis.technique_confusion(run_db)
        assert rows
        for r in rows:
            assert {"arm", "true_ttp", "n", "exact_pct", "parent_pct",
                    "not_detected_pct", "top_wrong"} <= set(r)
            assert 0.0 <= r["exact_pct"] <= 1.0

    def test_empty_when_no_runs(self, tmp_path):
        db = str(tmp_path / "e.db")
        state_cache.init_state_cache(db).close()
        assert failure_analysis.technique_confusion(db) == []

    def test_empty_when_runs_but_no_agent_outputs(self, tmp_path):
        # simulates an OLD run (predating agent_outputs capture): runs + scores exist
        # but no captured proposals -> must return [] (not a misleading all-missed table)
        db = str(tmp_path / "old.db")
        man = str(tmp_path / "m")
        gen_runner.generate("dev", db_path=db, manifests_dir=man)
        experiment.run_experiment(arms=("A4",), scenario_set="dev",
                                  category="multi_stage_kill_chain", seeds=1,
                                  db_path=db, manifests_dir=man, auto_generate=False)
        conn = state_cache.connect(db)
        conn.execute("DELETE FROM agent_outputs")     # strip captured outputs
        conn.commit(); conn.close()
        assert failure_analysis.technique_confusion(db) == []
