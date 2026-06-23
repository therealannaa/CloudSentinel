"""Pluggable LLM client for the LLM arms (A1-A3).

Two backends, identical interface:
  - DeterministicClient (default): applies detection signatures locally. Runs with
    NO API key, so the whole ablation pipeline is testable offline. Seed-invariant
    (run-to-run variance = 0), which is reported honestly.
  - GeminiClient: real google-generativeai calls, used automatically when
    GEMINI_API_KEY is set and the SDK is installed. Pin the model + record usage.

`analyze()` returns Candidates and an approximate token cost. For the deterministic
backend the token cost is *estimated* from input size so the C3 cost/latency
analysis (A2 vs A3) is non-degenerate even offline; the Gemini backend reports
real usage.
"""
from __future__ import annotations

import json
import os

from benchmark.arms.base import ArmEvent, Candidate
from benchmark.arms import signatures


def _est_tokens(events):
    chars = sum(len(json.dumps(e.raw, default=str)) for e in events)
    return chars // 4  # ~4 chars/token


class DeterministicClient:
    """Offline backend: signature-based detection. No network, no key."""
    name = "deterministic"

    def analyze(self, events: list[ArmEvent], role: str = "generalist",
                seed: int = 0):
        candidates = []
        for e in events:
            ttp = signatures.detect(e.source, e.raw)
            if ttp:
                candidates.append(Candidate(e.event_id, e.source, ttp, e.event_time))
        # deterministic backend ignores seed (results identical) -> 0 variance
        return candidates, _est_tokens(events)


class GeminiClient:
    """Real LLM backend. Activated when GEMINI_API_KEY is set + SDK installed."""
    name = "gemini"

    def __init__(self, model="gemini-2.0-flash", api_key=None):
        import google.generativeai as genai  # imported lazily
        self.model_name = model
        genai.configure(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self._genai = genai
        self._model = genai.GenerativeModel(model)

    _PROMPT = (
        "You are a {role} cloud security analyst. Below are AWS telemetry events as "
        "JSON. Identify which events are part of an attack and map each to a single "
        "MITRE ATT&CK-for-Cloud technique id (e.g. T1098.001). Reply ONLY with a JSON "
        "list of objects: [{{\"event_id\": str, \"ttp_id\": str}}]. Events:\n{events}"
    )

    def analyze(self, events, role="generalist", seed=0):
        payload = [{"event_id": e.event_id, "source": e.source,
                    "event_time": e.event_time, **e.raw} for e in events]
        prompt = self._PROMPT.format(role=role, events=json.dumps(payload)[:200_000])
        resp = self._model.generate_content(
            prompt, generation_config={"temperature": 0.7, "response_mime_type": "application/json"})
        by_id = {e.event_id: e for e in events}
        candidates = []
        try:
            for item in json.loads(resp.text):
                ev = by_id.get(item.get("event_id"))
                if ev and item.get("ttp_id"):
                    candidates.append(Candidate(ev.event_id, ev.source, item["ttp_id"], ev.event_time))
        except (json.JSONDecodeError, AttributeError, TypeError):
            pass
        usage = getattr(resp, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", 0) if usage else 0
        return candidates, int(tokens)


def get_client(prefer_real=True):
    """Return GeminiClient if usable, else the deterministic backend."""
    if prefer_real and os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiClient(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        except Exception:
            pass
    return DeterministicClient()
