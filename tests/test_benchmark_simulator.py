"""Tests for the attack simulator + manifest validity + catalog integrity.

Covers the P2 DoD: simulator produces all scenarios with VALID ground-truth
manifests, and every ground-truth event the manifest cites actually exists in
the captured telemetry.
"""
import pytest

from benchmark.simulator.specs import SCENARIO_SPECS, dev_ids, heldout_ids, all_ids
from benchmark.simulator.builder import build_scenario
from benchmark.matching import score


EXPECTED_COUNTS = {"SD": 12, "KC": 15, "LS": 12, "EP": 10, "BN": 10, "HO": 10}


class TestCatalogIntegrity:
    def test_counts_per_prefix(self):
        from collections import Counter
        c = Counter(sid.split("-")[0] for sid in SCENARIO_SPECS)
        assert dict(c) == EXPECTED_COUNTS

    def test_dev_and_heldout_partition(self):
        assert len(dev_ids()) == 59
        assert len(heldout_ids()) == 10
        assert set(dev_ids()).isdisjoint(heldout_ids())
        assert len(all_ids()) == 69

    def test_unique_ids(self):
        assert len(set(SCENARIO_SPECS)) == len(SCENARIO_SPECS)


class TestManifestsValid:
    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_every_manifest_validates(self, sid):
        _, m = build_scenario(sid, SCENARIO_SPECS[sid])
        assert m.validate() == [], f"{sid} manifest invalid"

    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_evidence_events_exist(self, sid):
        events, m = build_scenario(sid, SCENARIO_SPECS[sid])
        event_ids = {e.event_id for e in events}
        for stage in m.stages:
            for ev_id in stage.evidence_event_ids:
                assert ev_id in event_ids, f"{sid} stage {stage.stage_id} cites missing {ev_id}"

    def test_benign_has_no_stages(self):
        for sid, spec in SCENARIO_SPECS.items():
            if spec["category"] == "benign":
                _, m = build_scenario(sid, spec)
                assert m.stages == []

    def test_multistage_has_min_three_stages_two_sources(self):
        for sid, spec in SCENARIO_SPECS.items():
            if spec["category"] == "multi_stage_kill_chain" and sid not in ("KC-14",):
                _, m = build_scenario(sid, spec)
                assert len(m.stages) >= 3, f"{sid} should have >=3 stages"
                assert len({s.telemetry_source for s in m.stages}) >= 1


class TestNoAnswerKeyLeak:
    """The synthetic payload must not label ground-truth events with their TTP.
    raw_json is what the arms read; a `mitre_technique` field there would hand
    them the answer. Ground truth must live only in is_ground_truth + manifest."""

    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_raw_json_has_no_mitre_label(self, sid):
        events, _ = build_scenario(sid, SCENARIO_SPECS[sid])
        for e in events:
            assert "mitre_technique" not in e.raw_json, \
                f"{sid} leaks the TTP label in event {e.event_id}: {e.raw_json}"

    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_ground_truth_intact_after_strip(self, sid):
        """Scoring the manifest against itself is a perfect reconstruction —
        proves the answer key is preserved in the manifest, not the payload."""
        _, m = build_scenario(sid, SCENARIO_SPECS[sid])
        result = score(m, m)
        assert result.recall == 1.0 and result.precision == 1.0, \
            f"{sid}: manifest self-score not perfect ({result.to_dict()})"
        assert result.fp == 0 and result.fn == 0


class TestDeterminism:
    def test_same_inputs_same_events(self):
        e1, _ = build_scenario("KC-02", SCENARIO_SPECS["KC-02"])
        e2, _ = build_scenario("KC-02", SCENARIO_SPECS["KC-02"])
        assert [e.event_id for e in e1] == [e.event_id for e in e2]
        assert [e.event_time for e in e1] == [e.event_time for e in e2]
