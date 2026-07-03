"""Tests for benchmark/tcp_robustness.py — DoD item 11.

Key invariants verified:
  1. At ΔT=0, a perfect arm has order_penalty=0 and order_aware_recall=1.0
     (generator assigns strictly-increasing timestamps per stage).
  2. Recall is invariant to ΔT (matching function does not use timestamps).
  3. Shifting an intermediate source's events backward far enough causes
     order_penalty > 0 (stage appears earlier than ground truth says it should).
  4. Shifting the LAST stage's events forward does not affect ordering
     (it stays last regardless).
  5. robustness_threshold identifies the correct minimum |ΔT|.
  6. Benign scenarios (no stages) are silently skipped by run_all.
"""
from __future__ import annotations

import dataclasses

import pytest

from benchmark import tcp_robustness as tr
from benchmark.simulator.builder import build_scenario
from benchmark.simulator.specs import SCENARIO_SPECS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _manifest(sid="KC-02"):
    _, m = build_scenario(sid, SCENARIO_SPECS[sid])
    return m.to_dict()


def _sources(manifest):
    return {s["telemetry_source"] for s in manifest["stages"]}


# ---------------------------------------------------------------------------
# Unit tests on the sweep primitive
# ---------------------------------------------------------------------------

class TestSweepAt0:
    """ΔT = 0 must yield a perfect score for every multi-stage scenario."""

    @pytest.mark.parametrize("sid", [
        "KC-01", "KC-02", "KC-03", "KC-04", "KC-05",
    ])
    def test_zero_delta_perfect_ordering(self, sid):
        md = _manifest(sid)
        for source in _sources(md):
            rows = tr.sweep(sid, md, source, [0])
            assert len(rows) == 1
            r = rows[0]
            assert r.recall == 1.0, f"{sid}/{source}: recall should be 1.0 at ΔT=0"
            assert r.order_penalty == 0.0, (
                f"{sid}/{source}: order_penalty should be 0 at ΔT=0, got {r.order_penalty}"
            )
            assert r.order_aware_recall == 1.0, (
                f"{sid}/{source}: oar should be 1.0 at ΔT=0"
            )


class TestRecallInvariance:
    """Recall must not change as ΔT varies — timestamps are not used in matching."""

    def test_recall_constant_across_sweep(self):
        md = _manifest("KC-02")
        dt_range = [-600, -300, -120, -60, 0, 60, 120, 300, 600]
        rows = tr.sweep("KC-02", md, "S3", dt_range)
        recalls = {r.recall for r in rows}
        assert recalls == {1.0}, f"recall varied across ΔT sweep: {recalls}"


class TestOrderDegradation:
    """Shifting an intermediate source backward far enough must scramble order."""

    def test_large_backward_shift_raises_penalty(self):
        # KC-02 stage order: CT(00:00) → CT(00:01) → S3(00:02) → VPC(00:03)
        # Shifting S3 by -180s puts S3 events at 23:59 — before all CT stages.
        # The correlator then assigns S3 first → order mismatch for ground-truth stage 3.
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "S3", [-180])
        r = rows[0]
        assert r.recall == 1.0, "recall must be unaffected"
        assert r.order_penalty > 0.0, (
            "shifting S3 back 180 s must cause order_penalty > 0"
        )
        assert r.order_aware_recall < 1.0

    def test_last_stage_forward_shift_does_not_degrade(self):
        # KC-02 stage 4 is VPC — already last. Shifting it further forward
        # keeps it last, so order is preserved.
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "VPC", [300, 600, 900])
        for r in rows:
            assert r.order_penalty == 0.0, (
                f"shifting the last stage (VPC) forward by {r.delta_t_seconds}s "
                f"should not disrupt order, got penalty={r.order_penalty}"
            )

    def test_order_aware_recall_lte_recall(self):
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "S3", list(range(-900, 901, 60)))
        for r in rows:
            assert r.order_aware_recall <= r.recall + 1e-9, (
                f"order_aware_recall ({r.order_aware_recall}) > recall ({r.recall})"
            )


class TestRobustnessThreshold:
    """robustness_threshold must return the first |ΔT| where penalty > 0."""

    def test_threshold_found_for_intermediate_source(self):
        md = _manifest("KC-02")
        # Use fine-grained sweep around the 60-second inter-stage gap.
        # Stages: CT@00:00, CT@00:01, S3@00:02, VPC@00:03.
        # Shifting S3 back > 60 s puts it before CT stage 2 (at 00:01) → disruption.
        dt_range = list(range(-120, 1, 1))
        rows = tr.sweep("KC-02", md, "S3", dt_range)
        thresholds = tr.robustness_threshold(rows)
        thresh = thresholds[("KC-02", "S3")]
        assert thresh is not None, "threshold must be detected"
        # The inter-stage gap is 60 s, so the threshold is 61 s backward.
        assert 60 <= thresh <= 70, (
            f"expected threshold near 61 s for KC-02/S3, got {thresh}"
        )

    def test_no_threshold_for_last_stage(self):
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "VPC", [60, 120, 300, 600, 900])
        thresholds = tr.robustness_threshold(rows)
        assert thresholds[("KC-02", "VPC")] is None, (
            "last stage (VPC) forward shifts must never trigger threshold"
        )


# ---------------------------------------------------------------------------
# run_all integration
# ---------------------------------------------------------------------------

class TestRunAll:
    def test_benign_skipped(self):
        """Benign scenarios have no stages → no sources → run_all skips them."""
        md = _manifest("BN-01")
        assert md["stages"] == []
        results = tr.run_all({"BN-01": md}, delta_t_range=[0])
        assert results == [], "benign scenario must produce no rows"

    def test_multi_scenario(self):
        sids = ["KC-01", "KC-02", "KC-03"]
        manifests = {sid: _manifest(sid) for sid in sids}
        dt_range = [-120, 0, 120]
        results = tr.run_all(manifests, delta_t_range=dt_range)
        assert len(results) > 0
        # Every source that appears in a scenario's stages must be swept.
        for sid, md in manifests.items():
            for source in _sources(md):
                scenario_source_rows = [
                    r for r in results
                    if r.scenario_id == sid and r.perturbed_source == source
                ]
                assert len(scenario_source_rows) == len(dt_range), (
                    f"{sid}/{source}: expected {len(dt_range)} rows, got "
                    f"{len(scenario_source_rows)}"
                )

    def test_source_filter(self):
        md = _manifest("KC-02")
        results = tr.run_all({"KC-02": md}, delta_t_range=[0], sources=["S3"])
        assert all(r.perturbed_source == "S3" for r in results)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

class TestOutputHelpers:
    def test_to_csv(self, tmp_path):
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "S3", [-60, 0, 60])
        path = str(tmp_path / "out.csv")
        tr.to_csv(rows, path)
        import csv as csv_mod
        with open(path) as f:
            reader = list(csv_mod.DictReader(f))
        assert len(reader) == 3
        assert set(reader[0].keys()) == {
            "scenario_id", "perturbed_source", "delta_t_seconds",
            "recall", "order_penalty", "order_aware_recall",
        }

    def test_print_report_runs(self, capsys):
        md = _manifest("KC-02")
        rows = tr.sweep("KC-02", md, "S3", [0, 60])
        tr.print_report(rows)
        out = capsys.readouterr().out
        assert "KC-02" in out
        assert "S3" in out

    def test_candidates_from_manifest(self):
        md = _manifest("KC-02")
        cands = tr.candidates_from_manifest(md)
        n_evidence = sum(len(s["evidence_event_ids"]) for s in md["stages"])
        assert len(cands) == n_evidence
        # Every candidate's event_id must appear in some stage's evidence list.
        all_eids = {eid for s in md["stages"] for eid in s["evidence_event_ids"]}
        assert {c.event_id for c in cands} == all_eids
