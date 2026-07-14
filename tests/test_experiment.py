"""End-to-end ablation runner tests (P3): generate -> run A1-A4 -> score -> persist."""
import pytest

from benchmark import experiment, state_cache, analysis, runner as gen_runner


@pytest.fixture
def generated(tmp_path):
    db = str(tmp_path / "exp.db")
    manifests = str(tmp_path / "manifests")
    gen_runner.generate("dev", db_path=db, manifests_dir=manifests)
    return db, manifests


class TestRunExperiment:
    def test_all_arms_run_and_persist(self, generated):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A1", "A2", "A3", "A4"), scenario_set="dev", seeds=2,
            db_path=db, manifests_dir=manifests, auto_generate=False)
        # 59 dev scenarios x 4 arms x 2 seeds
        assert len(results) == 59 * 4 * 2

        conn = state_cache.connect(db)
        n_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        n_scores = conn.execute("SELECT COUNT(*) FROM scores").fetchone()[0]
        n_stages = conn.execute("SELECT COUNT(*) FROM reconstructed_stages").fetchone()[0]
        conn.close()
        assert n_runs == 59 * 4 * 2
        assert n_scores == n_runs
        assert n_stages > 0

    def test_a4_zero_cost_llm_arms_nonzero(self, generated):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A2", "A4"), scenario_set="dev", seeds=1,
            db_path=db, manifests_dir=manifests, auto_generate=False)
        a4 = [r for r in results if r["arm"] == "A4"]
        a2 = [r for r in results if r["arm"] == "A2"]
        assert all(r["token_cost"] == 0 for r in a4)
        assert sum(r["token_cost"] for r in a2) > 0

    def test_resume_skips_completed_runs(self, generated):
        db, manifests = generated
        # first pass: A4 on multi-stage, 1 seed
        first = experiment.run_experiment(
            arms=("A4",), scenario_set="dev", seeds=1, category="multi_stage_kill_chain",
            db_path=db, manifests_dir=manifests, auto_generate=False)
        assert not any(r.get("resumed") for r in first)
        # second pass with resume: everything already scored -> all skipped/reloaded
        second = experiment.run_experiment(
            arms=("A4",), scenario_set="dev", seeds=1, category="multi_stage_kill_chain",
            db_path=db, manifests_dir=manifests, auto_generate=False, resume=True)
        assert len(second) == 15 and all(r.get("resumed") for r in second)
        # scores identical to the first pass (nothing re-run)
        r1 = {r["run_id"]: r["recall"] for r in first}
        assert all(abs(r["recall"] - r1[r["run_id"]]) < 1e-9 for r in second)

    def test_resume_runs_only_missing_seed(self, generated):
        db, manifests = generated
        experiment.run_experiment(arms=("A4",), scenario_set="dev", seeds=1,
                                  category="multi_stage_kill_chain", db_path=db,
                                  manifests_dir=manifests, auto_generate=False)
        # now ask for 2 seeds with resume: seed 0 exists -> reloaded; seed 1 -> fresh
        res = experiment.run_experiment(
            arms=("A4",), scenario_set="dev", seeds=2, category="multi_stage_kill_chain",
            db_path=db, manifests_dir=manifests, auto_generate=False, resume=True)
        resumed = [r for r in res if r.get("resumed")]
        fresh = [r for r in res if not r.get("resumed")]
        assert len(resumed) == 15 and len(fresh) == 15   # seed0 reloaded, seed1 new

    def test_category_filter_runs_only_that_category(self, generated):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A4",), scenario_set="dev", seeds=1, category="multi_stage_kill_chain",
            db_path=db, manifests_dir=manifests, auto_generate=False)
        assert len(results) == 15                                  # 15 KC scenarios
        assert {r["category"] for r in results} == {"multi_stage_kill_chain"}

    def test_deterministic_backend_zero_seed_variance(self, generated):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A1",), scenario_set="dev", seeds=3,
            db_path=db, manifests_dir=manifests, auto_generate=False)
        # same scenario across seeds must give identical recall (deterministic backend)
        by_scen = {}
        for r in results:
            by_scen.setdefault(r["scenario_id"], set()).add(r["recall"])
        assert all(len(v) == 1 for v in by_scen.values())


class TestAnalysis:
    def test_per_category_rows(self, generated):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A1", "A2", "A3", "A4"), scenario_set="dev", seeds=2,
            db_path=db, manifests_dir=manifests, auto_generate=False)
        rows = analysis.per_category(results)
        cats = {r["category"] for r in rows}
        arms = {r["arm"] for r in rows}
        assert arms == {"A1", "A2", "A3", "A4"}
        assert "multi_stage_kill_chain" in cats and "benign" in cats
        # each row carries the C3 fields
        for r in rows:
            assert "filtering_ratio" in r and "prefilter_recall" in r
            assert 0.0 <= r["recall"] <= 1.0

    def test_csv_export(self, generated, tmp_path):
        db, manifests = generated
        results = experiment.run_experiment(
            arms=("A4",), scenario_set="dev", seeds=1,
            db_path=db, manifests_dir=manifests, auto_generate=False)
        out = str(tmp_path / "res.csv")
        analysis.to_csv(analysis.per_category(results), out)
        import os
        assert os.path.exists(out) and os.path.getsize(out) > 0
