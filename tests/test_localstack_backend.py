"""Offline tests for the LocalStack execution backend.

These inject a fake boto3 (recording calls, returning canned responses) so the
executor/capture/bind/teardown logic is validated WITHOUT Docker or network. Live
capture is exercised separately by running `docker compose up` + the
`localstack-check` / `generate --environment localstack` commands on a networked host.
"""
import json
import pytest

from benchmark.simulator import localstack_backend as lsb
from benchmark.simulator.specs import SCENARIO_SPECS


class FakeService:
    def __init__(self, name, responses, calls):
        self.name, self.responses, self.calls = name, responses, calls

    def __getattr__(self, method):
        def call(**kw):
            self.calls.append((self.name, method, kw))
            return self.responses.get(method, {})
        return call


_RESPONSES = {
    "list_buckets": {"Buckets": [{"Name": "prod-data"}, {"Name": "app-assets"}]},
    "list_objects_v2": {"Contents": [{"Key": "obj-0"}]},
    "create_access_key": {"AccessKey": {"AccessKeyId": "AKIAFAKE"}},
    "create_security_group": {"GroupId": "sg-fake"},
    "run_instances": {"Instances": [{"InstanceId": "i-fake123"}]},
    "get_caller_identity": {"Arn": "arn:aws:iam::000:user/test"},
}


def fake_clients():
    calls = []
    services = ("s3", "iam", "ec2", "sts", "secretsmanager", "cloudtrail")
    clients = {s: FakeService(s, _RESPONSES, calls) for s in services}
    clients["_calls"] = calls
    return clients


class TestExecuteScenario:
    @pytest.mark.parametrize("sid", ["KC-01", "KC-02", "SD-01", "EP-01", "BN-01"])
    def test_runs_and_binds(self, sid):
        clients = fake_clients()
        events, manifest = lsb.run_scenario_localstack(sid, SCENARIO_SPECS[sid], clients)
        assert manifest.validate() == []
        assert all(e.environment == "localstack" for e in events)
        ev_ids = {e.event_id for e in events}
        for stage in manifest.stages:
            for eid in stage.evidence_event_ids:
                assert eid in ev_ids

    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_all_specs_execute_without_error(self, sid):
        clients = fake_clients()
        events, manifest = lsb.run_scenario_localstack(sid, SCENARIO_SPECS[sid], clients)
        assert manifest.validate() == []

    @pytest.mark.parametrize("sid", list(SCENARIO_SPECS))
    def test_no_answer_key_leak(self, sid):
        clients = fake_clients()
        events, _ = lsb.run_scenario_localstack(sid, SCENARIO_SPECS[sid], clients)
        for e in events:
            assert "mitre_technique" not in e.raw_json


class TestRealApiBehaviour:
    def test_setup_creates_resources(self):
        clients = fake_clients()
        lsb.run_scenario_localstack("SD-01", SCENARIO_SPECS["SD-01"], clients)
        methods = {(svc, m) for svc, m, _ in clients["_calls"]}
        assert ("s3", "create_bucket") in methods
        assert ("iam", "create_user") in methods
        assert ("secretsmanager", "create_secret") in methods

    def test_teardown_called(self):
        clients = fake_clients()
        lsb.run_scenario_localstack("SD-01", SCENARIO_SPECS["SD-01"], clients)
        methods = {(svc, m) for svc, m, _ in clients["_calls"]}
        assert ("s3", "delete_bucket") in methods
        assert ("iam", "delete_user") in methods

    def test_createaccesskey_captures_real_id(self):
        clients = fake_clients()
        events, _ = lsb.run_scenario_localstack("KC-01", SCENARIO_SPECS["KC-01"], clients)
        raws = [json.loads(e.raw_json) for e in events]
        ak = [r for r in raws if r.get("eventName") == "CreateAccessKey"]
        assert ak and ak[0]["accessKeyId"] == "AKIAFAKE"

    def test_network_events_flagged_synthetic(self):
        # KC-01 ends in a VPC exfil flow; LocalStack has no flow logs -> tagged
        clients = fake_clients()
        events, _ = lsb.run_scenario_localstack("KC-01", SCENARIO_SPECS["KC-01"], clients)
        vpc = [json.loads(e.raw_json) for e in events
               if json.loads(e.raw_json).get("synthetic_network")]
        assert vpc and all(v["synthetic_network"] for v in vpc)


class TestConnectivityGuard:
    def test_make_clients_without_boto3_raises(self):
        # this sandbox has no boto3 installed -> make_clients must fail cleanly
        import importlib.util
        if importlib.util.find_spec("boto3") is not None:
            pytest.skip("boto3 is installed; guard not exercised here")
        with pytest.raises(lsb.LocalStackUnavailable):
            lsb.make_clients()
