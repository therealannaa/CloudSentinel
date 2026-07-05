"""The four ablation arms (A1-A4) + shared detection machinery (Phase P3).

Arms consume only arm-visible telemetry (event_id, source, event_time, raw) and
emit a reconstructed kill chain in the manifest stage schema, scored by the
mechanical matching function. They never see `is_ground_truth` — that lives only
in the manifest and is used solely for offline measurement.

  A1  prefilter + 4 domain hunters + coordinator   (full CloudSentinel)
  A2  prefilter + single generalised agent          (isolates decomposition, H2)
  A3  no prefilter + single agent on raw logs        (isolates the pre-filter, C3)
  A4  prefilter + deterministic rules, NO LLM        (isolates the LLM, H1)

The LLM arms (A1-A3) use a pluggable LLMClient: a deterministic offline backend
(default — runs with no API key) or a Gemini backend (when GEMINI_API_KEY is set).
A4 is pure rules and uses no LLM at all.
"""
from .registry import get_arm, ARMS  # noqa: F401
from .base import ArmEvent, ArmResult  # noqa: F401
