"""Smoke tests for figure generation (skipped if matplotlib isn't installed)."""
import os
import pytest

pytest.importorskip("matplotlib")
from benchmark import plots


RESULTS = [
    {"arm": "A1", "category": "multi_stage_kill_chain", "recall": 0.11, "precision": 0.10,
     "f1": 0.10, "token_cost": 1540.0},
    {"arm": "A4", "category": "multi_stage_kill_chain", "recall": 0.91, "precision": 0.60,
     "f1": 0.72, "token_cost": 0.0},
    {"arm": "A1", "category": "single_domain", "recall": 0.17, "precision": 0.1, "f1": 0.1,
     "token_cost": 1300.0},
    {"arm": "A4", "category": "single_domain", "recall": 1.0, "precision": 0.5, "f1": 0.6,
     "token_cost": 0.0},
]
DETECTION = [
    {"arm": "A1", "category": "multi_stage_kill_chain", "event_recall": 0.95, "event_precision": 0.88},
    {"arm": "A4", "category": "multi_stage_kill_chain", "event_recall": 0.97, "event_precision": 0.73},
]
CONFUSION = [
    {"arm": "A1", "true_ttp": "T1098.001", "n": 18, "exact_pct": 0.0, "parent_pct": 0.0,
     "not_detected_pct": 0.2, "top_wrong": "[]"},
    {"arm": "A1", "true_ttp": "T1530", "n": 30, "exact_pct": 0.4, "parent_pct": 0.5,
     "not_detected_pct": 0.1, "top_wrong": "[]"},
]


def test_all_four_figures_render(tmp_path):
    o = str(tmp_path)
    for f in (plots.fig_per_category(RESULTS, f"{o}/cat.png"),
              plots.fig_cost_accuracy(RESULTS, "multi_stage_kill_chain", f"{o}/cost.png"),
              plots.fig_two_lens(RESULTS, DETECTION, "multi_stage_kill_chain", f"{o}/lens.png"),
              plots.fig_confusion(CONFUSION, f"{o}/conf.png", arm="A1")):
        assert os.path.exists(f) and os.path.getsize(f) > 0


def test_read_missing_returns_none():
    assert plots._read(None) is None
    assert plots._read("/no/such/file.csv") is None


def test_main_skips_absent_inputs(capsys):
    assert plots.main(["--results", "/nope.csv", "--outdir", "/tmp"]) == 1
    assert "no input CSVs" in capsys.readouterr().out
