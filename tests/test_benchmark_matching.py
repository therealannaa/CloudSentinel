"""Unit tests for the mechanical matching function (docs/week1/04).

The P2 Definition of Done requires the matching function to pass unit tests on
several scenarios. We test it against the simulator's own manifests (perfect,
partial, empty, out-of-order, benign).
"""
import copy
import pytest

from benchmark.matching import score
from benchmark.simulator.specs import SCENARIO_SPECS
from benchmark.simulator.builder import build_scenario


def manifest_dict(sid):
    _, m = build_scenario(sid, SCENARIO_SPECS[sid])
    return m.to_dict()


def reconstructed_from_manifest(m):
    """A perfect reconstruction = copy the manifest's stages verbatim."""
    return {"stages": copy.deepcopy(m["stages"])}


class TestPerfectMatch:
    @pytest.mark.parametrize("sid", ["KC-02", "KC-01", "SD-01", "KC-08"])
    def test_perfect_reconstruction_scores_1(self, sid):
        m = manifest_dict(sid)
        r = reconstructed_from_manifest(m)
        s = score(r, m)
        assert s.recall == 1.0 and s.precision == 1.0 and s.f1 == 1.0
        assert s.fp == 0 and s.fn == 0
        assert s.order_penalty == 0.0


class TestPartialAndEmpty:
    def test_partial_recall(self):
        m = manifest_dict("KC-02")            # 4 stages
        r = {"stages": copy.deepcopy(m["stages"][:2])}   # caught first 2
        s = score(r, m)
        assert s.tp == 2 and s.fn == 2 and s.fp == 0
        assert s.recall == 0.5

    def test_empty_reconstruction(self):
        m = manifest_dict("KC-02")
        s = score({"stages": []}, m)
        assert s.tp == 0 and s.recall == 0.0
        assert s.precision == 1.0      # no false positives reported

    def test_evidence_binding_blocks_wrong_reason(self):
        m = manifest_dict("SD-01")
        wrong = copy.deepcopy(m["stages"])
        wrong[0]["evidence_event_ids"] = ["totally-unrelated"]
        s = score({"stages": wrong}, m)
        assert s.tp == 0 and s.fn == 1   # right TTP, wrong evidence -> no credit


class TestOrderSensitivity:
    def test_out_of_order_penalised(self):
        m = manifest_dict("KC-02")
        rev = {"stages": list(reversed(copy.deepcopy(m["stages"])))}
        s = score(rev, m)
        assert s.tp == 4                      # all stages matched
        assert s.order_penalty > 0.0          # but penalised for order
        assert s.order_aware_recall < s.recall


class TestBenign:
    def test_benign_no_report_is_perfect(self):
        m = manifest_dict("BN-01")
        assert m["stages"] == []
        s = score({"stages": []}, m)
        assert s.recall == 1.0 and s.precision == 1.0

    def test_benign_false_positive(self):
        m = manifest_dict("BN-01")
        fake = {"stages": [{"stage_id": 1, "ttp_id": "T1530",
                            "telemetry_source": "S3",
                            "evidence_event_ids": ["x"], "timestamp_range": ["a", "b"]}]}
        s = score(fake, m)
        assert s.fp == 1 and s.precision == 0.0
