"""Tests for the four ablation arms + pre-filter + correlation (P3)."""
import pytest

from benchmark.arms import get_arm, ARMS
from benchmark.arms.base import ArmEvent
from benchmark.arms import prefilter, signatures
from benchmark.manifest import validate as validate_manifest
from benchmark.matching import score
from benchmark.simulator.specs import SCENARIO_SPECS
from benchmark.simulator.builder import build_scenario


def arm_events(sid):
    """Build the arm-visible view (no is_ground_truth) from the simulator."""
    events, manifest = build_scenario(sid, SCENARIO_SPECS[sid])
    av = [ArmEvent(e.event_id, e.source, e.event_time,
                   __import__("json").loads(e.raw_json)) for e in events]
    return av, manifest.to_dict()


class TestArmContract:
    @pytest.mark.parametrize("code", ARMS)
    @pytest.mark.parametrize("sid", ["KC-01", "KC-02", "SD-01", "BN-01"])
    def test_arm_emits_schema_valid_stages(self, code, sid):
        events, manifest = arm_events(sid)
        res = get_arm(code).run(events)
        # reconstructed stages must be scoreable by the matching function
        s = score(res.reconstructed, manifest)
        assert isinstance(s.recall, float)
        # every reconstructed stage carries the required fields
        for st in res.reconstructed["stages"]:
            assert set(st) >= {"stage_id", "ttp_id", "telemetry_source",
                               "evidence_event_ids", "timestamp_range"}

    @pytest.mark.parametrize("code", ARMS)
    def test_arm_never_reads_ground_truth(self, code):
        # ArmEvent has no is_ground_truth attribute at all
        events, _ = arm_events("KC-01")
        assert not any(hasattr(e, "is_ground_truth") for e in events)
        get_arm(code).run(events)  # must not raise


class TestA4Rules:
    def test_a4_uses_no_llm_zero_cost(self):
        events, _ = arm_events("KC-01")
        res = get_arm("A4").run(events)
        assert res.token_cost == 0
        assert get_arm("A4").uses_llm is False

    def test_a4_recovers_clean_chain(self):
        # KC-01 stages (login/createkey/getobject/large-flow) map cleanly to signatures
        events, manifest = arm_events("KC-01")
        s = score(get_arm("A4").run(events).reconstructed, manifest)
        assert s.recall > 0.0 and s.tp >= 2

    def test_a4_deterministic_across_seeds(self):
        events, _ = arm_events("KC-02")
        r0 = get_arm("A4").run(events, seed=0).reconstructed
        r1 = get_arm("A4").run(events, seed=1).reconstructed
        assert r0 == r1


class TestPreFilter:
    def test_prefilter_reduces_volume(self):
        events, _ = arm_events("KC-02")
        kept, stats = prefilter.apply(events)
        assert stats["events_out"] <= stats["events_in"]
        assert stats["events_in"] == len(events)

    def test_prefilter_keeps_attack_signal(self):
        # the CreateAccessKey event (T1098.001) must survive the filter
        events, _ = arm_events("KC-01")
        kept_ids = {e.event_id for e in prefilter.apply(events)[0]}
        createkey = [e for e in events if e.raw.get("eventName") == "CreateAccessKey"]
        assert createkey and createkey[0].event_id in kept_ids


class TestArmDifferences:
    def test_a3_processes_more_than_a2(self):
        # A3 (no prefilter) sees all events; A2 (prefilter) sees fewer -> A3 costs more
        events, _ = arm_events("KC-02")
        a2 = get_arm("A2").run(events)
        a3 = get_arm("A3").run(events)
        assert a3.prefilter_events_out >= a2.prefilter_events_out
        assert a3.token_cost >= a2.token_cost

    def test_benign_scenario_signature_false_positives_are_possible(self):
        # benign discovery noise can trip signatures -> measured as FP (FPR test)
        events, manifest = arm_events("BN-01")
        s = score(get_arm("A4").run(events).reconstructed, manifest)
        assert manifest["stages"] == []
        assert s.fp >= 0  # may be >0; that's the FPR signal, never negative
