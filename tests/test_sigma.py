"""Tests for the community Sigma baseline (arm SIGMA)."""
import json
import pytest

from benchmark.arms import get_arm
from benchmark.arms.base import ArmEvent
from benchmark.arms.sigma import sigma_detect, SigmaArm
from benchmark.matching import score
from benchmark.simulator.specs import SCENARIO_SPECS
from benchmark.simulator.builder import build_scenario


def arm_events(sid):
    events, manifest = build_scenario(sid, SCENARIO_SPECS[sid])
    av = [ArmEvent(e.event_id, e.source, e.event_time, json.loads(e.raw_json)) for e in events]
    return av, manifest.to_dict()


class TestSigmaDetect:
    def test_cloudtrail_rules(self):
        assert sigma_detect("CloudTrail", {"eventName": "CreateAccessKey"}) == "T1098.001"
        assert sigma_detect("CloudTrail", {"eventName": "StopLogging"}) == "T1562.008"
        assert sigma_detect("CloudTrail", {"eventName": "GetSecretValue"}) == "T1528"

    def test_s3_rules(self):
        assert sigma_detect("S3", {"operation": "GetObject"}) == "T1530"
        assert sigma_detect("S3", {"operation": "DeleteObject"}) == "T1485"

    def test_no_vpc_coverage(self):
        # community CloudTrail+S3 ruleset has no flow-log rules
        assert sigma_detect("VPC", {"action": "REJECT"}) is None
        assert sigma_detect("VPC", {"bytes": 250_000_000, "dstport": 443}) is None


class TestSigmaArm:
    def test_registered_and_no_llm(self):
        arm = get_arm("SIGMA")
        assert isinstance(arm, SigmaArm) and arm.uses_llm is False

    def test_zero_token_cost_and_valid_schema(self):
        events, manifest = arm_events("KC-03")   # all-CloudTrail chain -> SIGMA does well
        res = get_arm("SIGMA").run(events)
        assert res.token_cost == 0
        s = score(res.reconstructed, manifest)
        assert isinstance(s.recall, float)
        for st in res.reconstructed["stages"]:
            assert set(st) >= {"stage_id", "ttp_id", "telemetry_source", "evidence_event_ids"}

    def test_misses_vpc_exfil_stage(self):
        # KC-01 ends in a T1537 VPC exfil flow; SIGMA has no VPC rules -> must miss it
        events, manifest = arm_events("KC-01")
        recon = get_arm("SIGMA").run(events).reconstructed
        assert not any(st["telemetry_source"] == "VPC" for st in recon["stages"])
        s = score(recon, manifest)
        assert s.recall < 1.0            # at least the exfil stage is missed

    def test_differs_from_a4_on_network(self):
        # A4 (team signatures, has VPC rules) should recover the VPC exfil that SIGMA misses
        events, manifest = arm_events("KC-01")
        a4 = score(get_arm("A4").run(events).reconstructed, manifest)
        sigma = score(get_arm("SIGMA").run(events).reconstructed, manifest)
        assert a4.recall >= sigma.recall


class TestSigmaInExperiment:
    def test_runs_and_scores(self, tmp_path):
        from benchmark import experiment, runner as gen_runner, state_cache
        db = str(tmp_path / "s.db")
        man = str(tmp_path / "m")
        gen_runner.generate("dev", db_path=db, manifests_dir=man)
        res = experiment.run_experiment(arms=("A4", "SIGMA"), scenario_set="dev", seeds=1,
                                        db_path=db, manifests_dir=man, auto_generate=False)
        assert {r["arm"] for r in res} == {"A4", "SIGMA"}
        conn = state_cache.connect(db)
        n = conn.execute("SELECT COUNT(*) FROM runs WHERE arm='SIGMA'").fetchone()[0]
        conn.close()
        assert n == 59
