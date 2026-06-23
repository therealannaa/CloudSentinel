"""Arm registry."""
from __future__ import annotations

from benchmark.arms.arms_impl import A1Multi, A2Single, A3SingleRaw, A4Rules

ARMS = ("A1", "A2", "A3", "A4")

_FACTORIES = {
    "A1": A1Multi,
    "A2": A2Single,
    "A3": A3SingleRaw,
    "A4": A4Rules,
}


def get_arm(code, client=None):
    """Instantiate an arm. `client` (shared LLMClient) lets the runner reuse one
    Gemini/deterministic client across the LLM arms; A4 ignores it."""
    code = code.upper()
    if code not in _FACTORIES:
        raise KeyError(f"unknown arm {code!r}; choose from {ARMS}")
    factory = _FACTORIES[code]
    if code == "A4":
        return factory()
    return factory(client=client)
