"""Tests for the P4 statistics module (bootstrap CIs, effect sizes, permutation
p-values, Holm-Bonferroni, H1/H2 verdicts)."""
import pytest

from benchmark import stats


# --- primitives --------------------------------------------------------------

class TestPrimitives:
    def test_bootstrap_ci_constant(self):
        lo, hi, point = stats.bootstrap_ci([0.8, 0.8, 0.8, 0.8])
        assert lo == hi == point == 0.8

    def test_bootstrap_ci_brackets_mean(self):
        lo, hi, point = stats.bootstrap_ci([0.2, 0.4, 0.6, 0.8, 1.0], n_boot=2000)
        assert lo <= point <= hi and abs(point - 0.6) < 1e-9

    def test_cohens_dz_zero_and_value(self):
        assert stats.cohens_dz([0.0, 0.0, 0.0]) == 0.0
        # constant positive diff -> sd 0 -> infinite effect
        assert stats.cohens_dz([0.3, 0.3, 0.3]) == float("inf")
        assert stats.cohens_dz([0.2, 0.4, 0.6]) > 0

    def test_permutation_pvalue_extremes(self):
        assert stats.permutation_pvalue([0.0, 0.0, 0.0]) == 1.0
        # strong consistent effect -> small p
        p = stats.permutation_pvalue([0.4] * 10, n_perm=2000)
        assert p < 0.05

    def test_holm_bonferroni(self):
        out = stats.holm_bonferroni([0.001, 0.04])
        assert out[0]["reject"] is True          # 0.001 <= 0.05/2
        # 0.04 vs 0.05/1 = 0.05 -> reject too
        assert out[1]["reject"] is True
        out2 = stats.holm_bonferroni([0.20, 0.04])
        assert out2[0]["reject"] is False and out2[1]["reject"] is False  # step-down stops


# --- synthetic result fixtures -----------------------------------------------

def _results(arm_recall, arm_f1=None, category="multi_stage_kill_chain", n=15, seeds=3):
    """Build per-run dicts where each arm has a fixed per-scenario recall/f1."""
    rows = []
    for arm, rec in arm_recall.items():
        f1 = (arm_f1 or {}).get(arm, rec)
        for i in range(n):
            for s in range(seeds):
                rows.append({"arm": arm, "scenario_id": f"KC-{i:02d}", "category": category,
                             "seed": s, "recall": rec, "precision": rec, "f1": f1})
    return rows


class TestPairedComparison:
    def test_paired_diff_and_compare(self):
        res = _results({"A2": 0.9, "A4": 0.6})
        scen, diffs = stats.paired_differences(res, "A2", "A4", "multi_stage_kill_chain", "recall")
        assert len(scen) == 15 and all(abs(d - 0.3) < 1e-9 for d in diffs)
        c = stats.compare(res, "A2", "A4", "multi_stage_kill_chain", "recall")
        assert abs(c["mean_diff"] - 0.3) < 1e-9 and c["ci_excludes_0"]


class TestH1:
    def test_h1_supported_when_llm_beats_rules(self):
        res = _results({"A1": 0.85, "A2": 0.9, "A4": 0.6})   # best LLM A2, diff 0.3 >= 0.15
        h1 = stats.evaluate_h1(res, margin=0.15)
        assert h1["verdict"] == "SUPPORTED" and "A2" in h1["test"]

    def test_h1_not_supported_when_rules_competitive(self):
        res = _results({"A1": 0.62, "A2": 0.63, "A4": 0.60})  # diff 0.03 < 0.15
        h1 = stats.evaluate_h1(res, margin=0.15)
        assert h1["verdict"] == "NOT SUPPORTED"


class TestH2:
    def test_h2_fail_to_reject_when_equal(self):
        res = _results({"A1": 0.7, "A2": 0.7}, arm_f1={"A1": 0.7, "A2": 0.7})
        h2 = stats.evaluate_h2(res, band=0.05)
        assert h2["verdict"] == "FAIL TO REJECT"

    def test_h2_reject_when_multiagent_better(self):
        res = _results({"A1": 0.9, "A2": 0.7}, arm_f1={"A1": 0.9, "A2": 0.7})
        h2 = stats.evaluate_h2(res, band=0.05)
        assert h2["verdict"] == "REJECT" and "outperforms" in h2["interpretation"]


class TestFullReportAndDB:
    def test_full_report_structure(self):
        res = _results({"A1": 0.8, "A2": 0.82, "A4": 0.6})
        rep = stats.full_report(results=res)
        assert len(rep["primary_tests"]) == 2
        assert {r["arm"] for r in rep["per_category_recall"]} == {"A1", "A2", "A4"}
        assert "holm" in rep["primary_tests"][0]

    def test_loads_from_db_after_experiment(self, tmp_path):
        from benchmark import experiment, runner as gen_runner
        db = str(tmp_path / "e.db")
        man = str(tmp_path / "m")
        gen_runner.generate("dev", db_path=db, manifests_dir=man)
        experiment.run_experiment(arms=("A2", "A4"), scenario_set="dev", seeds=2,
                                  db_path=db, manifests_dir=man, auto_generate=False)
        loaded = stats.load_results(db)
        assert loaded and {r["arm"] for r in loaded} == {"A2", "A4"}
        rep = stats.full_report(db_path=db)
        assert "primary_tests" in rep

    def test_empty_db_reports_error(self, tmp_path):
        from benchmark import state_cache
        db = str(tmp_path / "empty.db")
        state_cache.init_state_cache(db).close()
        rep = stats.full_report(db_path=db)
        assert "error" in rep
