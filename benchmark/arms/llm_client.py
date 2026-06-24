"""Pluggable LLM client for the LLM arms (A1-A3).

Backends, identical interface (`analyze(events, role, seed) -> (candidates, tokens)`):
  - DeterministicClient (default): signature-based detection. No key, no network,
    fully offline/testable. Seed-invariant (run-to-run variance = 0, reported honestly).
  - OpenAICompatibleClient: any OpenAI-compatible /chat/completions endpoint — used for
    **Ollama** (local, free, no quota) and also Groq / OpenRouter / GitHub Models / etc.
    Activated when LLM_BASE_URL is set.
  - GeminiClient: google-generativeai. Activated when GEMINI_API_KEY is set.

Selection order (get_client): LLM_BASE_URL > GEMINI_API_KEY > deterministic.

Token cost: real backends report usage; the deterministic backend estimates it from
input size so the C3 cost analysis (A2 vs A3) is non-degenerate offline.
"""
from __future__ import annotations

import json
import os
import re
import time

from benchmark.arms.base import ArmEvent, Candidate
from benchmark.arms import signatures


class LLMError(RuntimeError):
    """Unrecoverable real-LLM failure (quota, unreachable server) after retries.
    Carries actionable guidance; the runner aborts rather than write zero-scores."""


_RETRYABLE = {"ResourceExhausted", "ServiceUnavailable", "TooManyRequests",
              "InternalServerError", "DeadlineExceeded"}

# The shared analyst prompt used by every real backend.
_ANALYST_PROMPT = (
    "You are a {role} cloud security analyst. Below are AWS telemetry events as JSON. "
    "Identify which events are part of an attack and map each to a single MITRE "
    "ATT&CK-for-Cloud technique id (e.g. T1098.001). Reply ONLY with a JSON list of "
    "objects: [{{\"event_id\": str, \"ttp_id\": str}}]. Events:\n{events}"
)


def _retry_delay(exc, attempt):
    hint = getattr(exc, "retry_delay", None)
    secs = getattr(hint, "seconds", None) if hint is not None else None
    if not secs:
        m = re.search(r"retry in ([\d.]+)s", str(exc))
        secs = float(m.group(1)) if m else None
    return min(secs if secs else 2 ** attempt, 30)


def _est_tokens(events):
    chars = sum(len(json.dumps(e.raw, default=str)) for e in events)
    return chars // 4  # ~4 chars/token


def _payload(events):
    return [{"event_id": e.event_id, "source": e.source,
             "event_time": e.event_time, **e.raw} for e in events]


def _extract_json_array(text):
    """Robustly pull a JSON array out of an LLM reply (small local models often wrap
    it in prose or markdown fences)."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\[.*\]", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


def _parse_candidates(text, events):
    by_id = {e.event_id: e for e in events}
    data = _extract_json_array(text)
    out = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                ev = by_id.get(item.get("event_id"))
                if ev and item.get("ttp_id"):
                    out.append(Candidate(ev.event_id, ev.source, item["ttp_id"], ev.event_time))
    return out


class DeterministicClient:
    """Offline backend: signature-based detection. No network, no key."""
    name = "deterministic"

    def analyze(self, events: list[ArmEvent], role: str = "generalist", seed: int = 0):
        candidates = []
        for e in events:
            ttp = signatures.detect(e.source, e.raw)
            if ttp:
                candidates.append(Candidate(e.event_id, e.source, ttp, e.event_time))
        return candidates, _est_tokens(events)   # seed-invariant by design


class OpenAICompatibleClient:
    """Any OpenAI-compatible chat endpoint. Default target: local Ollama.

    Env: LLM_BASE_URL (e.g. http://localhost:11434/v1), LLM_API_KEY (Ollama: "ollama"),
    LLM_MODEL (e.g. llama3.1). Set LLM_PROVIDER to label the run (else auto-detected)."""

    def __init__(self, base_url=None, api_key=None, model=None, timeout=None):
        self.base_url = (base_url or os.environ["LLM_BASE_URL"]).rstrip("/")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "ollama")
        self.model = model or os.getenv("LLM_MODEL", "llama3.1")
        self.timeout = timeout or int(os.getenv("LLM_TIMEOUT", "180"))  # local models can be slow
        self.name = os.getenv("LLM_PROVIDER") or ("ollama" if "11434" in self.base_url
                                                  else "openai-compat")

    def _post(self, body, max_retries=5):
        import requests  # already a project dependency
        url = self.base_url + "/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        last = None
        for attempt in range(max_retries):
            try:
                r = requests.post(url, json=body, headers=headers, timeout=self.timeout)
                if r.status_code in (429, 500, 502, 503, 504):
                    last = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
                    time.sleep(min(2 ** attempt, 30))
                    continue
                r.raise_for_status()
                return r.json()
            except requests.exceptions.ConnectionError as e:
                raise LLMError(
                    f"Cannot reach the LLM server at {url}.\n"
                    f"  - For Ollama: start it with `ollama serve` and pull the model "
                    f"with `ollama pull {self.model}`.\n"
                    f"  - Check LLM_BASE_URL / LLM_MODEL.") from e
            except requests.exceptions.RequestException as e:
                last = e
                time.sleep(min(2 ** attempt, 30))
        raise LLMError(
            f"LLM call to {url} failed after {max_retries} retries: {last}\n"
            f"  - Is the model `{self.model}` pulled and serving?\n"
            f"  - Try a smaller/faster model or fewer scenarios (--limit).")

    def analyze(self, events, role="generalist", seed=0):
        prompt = _ANALYST_PROMPT.format(role=role, events=json.dumps(_payload(events))[:200_000])
        body = {"model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7, "seed": seed, "stream": False}
        data = self._post(body)
        content = (((data.get("choices") or [{}])[0]).get("message") or {}).get("content", "")
        cands = _parse_candidates(content, events)
        tokens = (data.get("usage") or {}).get("total_tokens") or _est_tokens(events)
        return cands, int(tokens)


class GeminiClient:
    """google-generativeai backend. Activated when GEMINI_API_KEY is set + SDK installed."""
    name = "gemini"

    def __init__(self, model="gemini-2.0-flash", api_key=None):
        import google.generativeai as genai  # imported lazily
        self.model_name = model
        genai.configure(api_key=api_key or os.environ["GEMINI_API_KEY"])
        self._genai = genai
        self._model = genai.GenerativeModel(model)

    def _generate(self, prompt, max_retries=5):
        last = None
        for attempt in range(max_retries):
            try:
                return self._model.generate_content(
                    prompt, generation_config={"temperature": 0.7,
                                               "response_mime_type": "application/json"})
            except Exception as e:  # noqa: BLE001 - classify by type name (lazy SDK)
                last = e
                if type(e).__name__ not in _RETRYABLE or attempt == max_retries - 1:
                    break
                time.sleep(_retry_delay(e, attempt))
        raise LLMError(
            f"Gemini call failed ({type(last).__name__}): {last}\n"
            "  - Quota/limit=0 usually means this model isn't on your free tier or the "
            "daily cap is hit.\n"
            "  - Try a free-tier model:  export GEMINI_MODEL=gemini-1.5-flash\n"
            "  - Or use local Ollama (free, no quota) — see README.\n"
            "  - Validate cheaply first:  run-arms --arms A2 --limit 1 --seeds 1") from last

    def analyze(self, events, role="generalist", seed=0):
        prompt = _ANALYST_PROMPT.format(role=role, events=json.dumps(_payload(events))[:200_000])
        resp = self._generate(prompt)
        cands = _parse_candidates(getattr(resp, "text", ""), events)
        usage = getattr(resp, "usage_metadata", None)
        tokens = getattr(usage, "total_token_count", 0) if usage else 0
        return cands, int(tokens)


def get_client(prefer_real=True):
    """Pick the LLM backend: LLM_BASE_URL (Ollama/OpenAI-compat) > GEMINI_API_KEY >
    deterministic offline. Construction failures fall through to the next option."""
    if prefer_real and os.getenv("LLM_BASE_URL"):
        try:
            return OpenAICompatibleClient()
        except Exception:
            pass
    if prefer_real and os.getenv("GEMINI_API_KEY"):
        try:
            return GeminiClient(model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"))
        except Exception:
            pass
    return DeterministicClient()
