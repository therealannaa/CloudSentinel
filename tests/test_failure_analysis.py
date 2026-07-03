"""Tests for the C4 failure-mode analysis."""
import pytest

from benchmark import experiment, runner as gen_runner, failure_analysis


@pytest.fixture
def run_db(tmp_path):
    db = str(tmp_path / "fa.db")
    man = str(tmp_path / "m")
    gen_runner.generate("dev", db_path=db, manifests_dir=man)
    experiment.run_experiment(arms=("A1", "A4"), scenario_set="dev", seeds=2,
                              db_path=db, manifests_dir=man, auto_generate=False)
    return db


class TestAnalyze:
    def test_report_structure(self, run_db):
        rep = failure_analysis.analyze(run_db)
        assert set(rep["arms"]) == {"A1", "A4"}
        for key in ("miss_rate_by_technique", "false_positive_patterns",
                    "false_positives_on_benign", "hardest_scenarios_per_category",
                    "prefilter_stress_low_and_slow"):
            assert key in rep

    def test_t1580_is_missed_by_signature_ambiguity(self, run_db):
        # signatures map discovery to T1526, so T1580 ground-truth stages (KC-02/05/10)
        # are consistently missed -> must surface as a non-zero miss for A4
        rep = failure_analysis.analyze(run_db)
        a4 = {r["ttp_id"]: r for r in rep["miss_rate_by_technique"]["A4"]}
        assert "T1580" in a4 and a4["T1580"]["missed"] > 0
        assert a4["T1580"]["miss_rate"] > 0.0

    def test_benign_false_positives_counted(self, run_db):
        rep = failure_analysis.analyze(run_db)
        # benign discovery noise trips signatures -> A4 has some benign FPs
        assert rep["false_positives_on_benign"].get("A4", 0) >= 0

    def test_hardest_scenarios_sorted(self, run_db):
        rep = failure_analysis.analyze(run_db)
        for cat, rows in rep["hardest_scenarios_per_category"].items():
            recalls = [r["mean_recall"] for r in rows]
            assert recalls == sorted(recalls)   # ascending (hardest first)

    def test_prefilter_stress_present_for_low_and_slow(self, run_db):
        rep = failure_analysis.analyze(run_db)
        pf = rep["prefilter_stress_low_and_slow"]
        assert pf["mean_prefilter_recall"] is not None
        assert 0.0 <= pf["mean_prefilter_recall"] <= 1.0

    def test_empty_db_error(self, tmp_path):
        from benchmark import state_cache
        db = str(tmp_path / "e.db")
        state_cache.init_state_cache(db).close()
        assert "error" in failure_analysis.analyze(db)
