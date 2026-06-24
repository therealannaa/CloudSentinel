"""Offline tests for the LLM backend selection + the Gemini client's prompt/parse
logic (mocked — no API key or network needed).

A live Gemini run is a one-command step on a machine with GEMINI_API_KEY set and
`pip install google-generativeai`; this verifies everything around the API call.
"""
import json
import pytest

from benchmark.arms import llm_client
from benchmark.arms.base import ArmEvent
from benchmark.arms.llm_client import DeterministicClient, GeminiClient, get_client


def _events():
    return [
        ArmEvent("e1", "CloudTrail", "2026-01-01T00:00:00", {"eventName": "CreateAccessKey"}),
        ArmEvent("e2", "S3", "2026-01-01T00:01:00", {"operation": "GetObject", "bucket": "b"}),
    ]


class TestBackendSelection:
    def test_default_is_deterministic_without_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        assert get_client().name == "deterministic"

    def test_falls_back_when_sdk_missing(self, monkeypatch):
        # key present but SDK import fails -> graceful fallback to deterministic
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")
        assert get_client(prefer_real=True).name == "deterministic"

    def test_deterministic_seed_invariant(self):
        c = DeterministicClient()
        a, _ = c.analyze(_events(), seed=0)
        b, _ = c.analyze(_events(), seed=7)
        assert [x.ttp_id for x in a] == [x.ttp_id for x in b]

    def test_deterministic_estimates_tokens(self):
        cands, tokens = DeterministicClient().analyze(_events())
        assert tokens > 0 and any(c.ttp_id == "T1098.001" for c in cands)


class FakeResp:
    def __init__(self, text, tokens=123):
        self.text = text
        self.usage_metadata = type("U", (), {"total_token_count": tokens})()


class FakeModel:
    def __init__(self, payload):
        self._payload = payload
        self.last_prompt = None

    def generate_content(self, prompt, generation_config=None):
        self.last_prompt = prompt
        return FakeResp(json.dumps(self._payload))


class TestGeminiClientParsing:
    def _client_with(self, payload, monkeypatch):
        c = GeminiClient.__new__(GeminiClient)        # bypass __init__ (no SDK/key)
        c.model_name = "gemini-2.0-flash"
        c._model = FakeModel(payload)
        return c

    def test_parses_candidates_from_json(self, monkeypatch):
        payload = [{"event_id": "e1", "ttp_id": "T1098.001"}]
        c = self._client_with(payload, monkeypatch)
        cands, tokens = c.analyze(_events(), role="CloudTrail")
        assert len(cands) == 1
        assert cands[0].event_id == "e1" and cands[0].ttp_id == "T1098.001"
        assert cands[0].telemetry_source == "CloudTrail"   # taken from the real event
        assert tokens == 123

    def test_ignores_unknown_event_ids(self, monkeypatch):
        payload = [{"event_id": "does-not-exist", "ttp_id": "T1530"}]
        c = self._client_with(payload, monkeypatch)
        cands, _ = c.analyze(_events())
        assert cands == []

    def test_survives_malformed_response(self, monkeypatch):
        c = GeminiClient.__new__(GeminiClient)
        c._model = type("M", (), {"generate_content":
                                  lambda self, p, generation_config=None: FakeResp("not json")})()
        cands, _ = c.analyze(_events())
        assert cands == []                              # no crash, empty result

    def test_prompt_includes_role_and_events(self, monkeypatch):
        c = self._client_with([], monkeypatch)
        c.analyze(_events(), role="S3 data")
        assert "S3 data" in c._model.last_prompt and "CreateAccessKey" in c._model.last_prompt
