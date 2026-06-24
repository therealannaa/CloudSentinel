"""Offline tests for the LLM backend selection + the Gemini client's prompt/parse
logic (mocked — no API key or network needed).

A live Gemini run is a one-command step on a machine with GEMINI_API_KEY set and
`pip install google-generativeai`; this verifies everything around the API call.
"""
import json
import pytest

from benchmark.arms import llm_client
from benchmark.arms.base import ArmEvent
from benchmark.arms.llm_client import (
    DeterministicClient, GeminiClient, OpenAICompatibleClient, get_client, LLMError)


def _events():
    return [
        ArmEvent("e1", "CloudTrail", "2026-01-01T00:00:00", {"eventName": "CreateAccessKey"}),
        ArmEvent("e2", "S3", "2026-01-01T00:01:00", {"operation": "GetObject", "bucket": "b"}),
    ]


class TestBackendSelection:
    def test_default_is_deterministic_without_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
        assert get_client().name == "deterministic"

    def test_llm_base_url_selects_openai_compatible(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("LLM_MODEL", "llama3.1")
        c = get_client()
        assert isinstance(c, OpenAICompatibleClient) and c.name == "ollama"

    def test_llm_base_url_takes_priority_over_gemini(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
        monkeypatch.setenv("GEMINI_API_KEY", "k")
        assert get_client().name == "ollama"

    def test_falls_back_when_client_construction_fails(self, monkeypatch):
        # key present but the Gemini client can't be built (missing SDK / bad config)
        # -> get_client must gracefully fall back to the deterministic backend
        monkeypatch.setenv("GEMINI_API_KEY", "fake-key")

        def boom(*a, **k):
            raise RuntimeError("no SDK / bad config")
        monkeypatch.setattr(llm_client, "GeminiClient", boom)
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


class FakeHTTPResponse:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def _chat_payload(content, total_tokens=42):
    return {"choices": [{"message": {"content": content}}],
            "usage": {"total_tokens": total_tokens}}


class TestOpenAICompatibleClient:
    def _client(self):
        return OpenAICompatibleClient(base_url="http://localhost:11434/v1",
                                      api_key="ollama", model="llama3.1")

    def test_parses_clean_json(self, monkeypatch):
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured["url"], captured["body"] = url, json
            return FakeHTTPResponse(_chat_payload('[{"event_id":"e1","ttp_id":"T1098.001"}]'))
        import requests
        monkeypatch.setattr(requests, "post", fake_post)
        cands, tokens = self._client().analyze(_events(), role="CloudTrail", seed=3)
        assert captured["url"].endswith("/chat/completions")
        assert captured["body"]["seed"] == 3 and captured["body"]["model"] == "llama3.1"
        assert len(cands) == 1 and cands[0].ttp_id == "T1098.001" and tokens == 42

    def test_extracts_json_from_markdown_prose(self, monkeypatch):
        # small local models often wrap the array in ```json fences + chatter
        msg = "Sure! Here you go:\n```json\n[{\"event_id\": \"e2\", \"ttp_id\": \"T1530\"}]\n```"
        import requests
        monkeypatch.setattr(requests, "post",
                            lambda *a, **k: FakeHTTPResponse(_chat_payload(msg)))
        cands, _ = self._client().analyze(_events())
        assert len(cands) == 1 and cands[0].event_id == "e2"

    def test_garbage_reply_yields_no_candidates(self, monkeypatch):
        import requests
        monkeypatch.setattr(requests, "post",
                            lambda *a, **k: FakeHTTPResponse(_chat_payload("I cannot help with that.")))
        cands, _ = self._client().analyze(_events())
        assert cands == []

    def test_connection_error_raises_actionable_llmerror(self, monkeypatch):
        import requests
        def boom(*a, **k):
            raise requests.exceptions.ConnectionError("refused")
        monkeypatch.setattr(requests, "post", boom)
        with pytest.raises(LLMError) as ei:
            self._client().analyze(_events())
        assert "ollama serve" in str(ei.value)

    def test_retries_on_http_500(self, monkeypatch):
        monkeypatch.setattr(llm_client.time, "sleep", lambda *_: None)
        calls = {"n": 0}

        def flaky(*a, **k):
            calls["n"] += 1
            if calls["n"] < 3:
                return FakeHTTPResponse({"error": "overloaded"}, status=503)
            return FakeHTTPResponse(_chat_payload("[]"))
        import requests
        monkeypatch.setattr(requests, "post", flaky)
        cands, _ = self._client().analyze(_events())
        assert calls["n"] == 3 and cands == []


class ResourceExhausted(Exception):
    """Mimics google.api_core.exceptions.ResourceExhausted (classified by name)."""


class TestRetryAndQuota:
    def _client(self, model):
        c = GeminiClient.__new__(GeminiClient)
        c._model = model
        return c

    def test_retries_then_succeeds(self, monkeypatch):
        monkeypatch.setattr(llm_client.time, "sleep", lambda *_: None)
        calls = {"n": 0}

        class FlakyModel:
            def generate_content(self, prompt, generation_config=None):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise ResourceExhausted("retry in 1s")
                return FakeResp(json.dumps([]))
        c = self._client(FlakyModel())
        cands, _ = c.analyze(_events())
        assert calls["n"] == 3 and cands == []

    def test_quota_raises_clean_llmerror(self, monkeypatch):
        monkeypatch.setattr(llm_client.time, "sleep", lambda *_: None)

        class DeadModel:
            def generate_content(self, prompt, generation_config=None):
                raise ResourceExhausted("quota exceeded, limit: 0")
        c = self._client(DeadModel())
        with pytest.raises(LLMError) as ei:
            c.analyze(_events())
        assert "GEMINI_MODEL" in str(ei.value)  # actionable guidance present

    def test_non_retryable_raises_immediately(self, monkeypatch):
        slept = {"n": 0}
        monkeypatch.setattr(llm_client.time, "sleep", lambda *_: slept.__setitem__("n", slept["n"] + 1))

        class BadKeyModel:
            def generate_content(self, prompt, generation_config=None):
                raise ValueError("invalid api key")  # not in _RETRYABLE
        with pytest.raises(LLMError):
            self._client(BadKeyModel()).analyze(_events())
        assert slept["n"] == 0  # did not retry/backoff on a non-retryable error
