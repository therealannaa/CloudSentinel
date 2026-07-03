"""Arm registry."""
from __future__ import annotations

from benchmark.arms.arms_impl import A1Multi, A2Single, A3SingleRaw, A4Rules
from benchmark.arms.sigma import SigmaArm

ARMS = ("A1", "A2", "A3", "A4")        # the four-arm ablation
BASELINES = ("SIGMA",)                 # external baselines (docs/week1/11); opt-in via --arms
NON_LLM = ("A4", "SIGMA")              # arms that take no LLM client

_FACTORIES = {
    "A1": A1Multi,
    "A2": A2Single,
    "A3": A3SingleRaw,
    "A4": A4Rules,
    "SIGMA": SigmaArm,
}


def get_arm(code, client=None):
    """Instantiate an arm. `client` (shared LLMClient) lets the runner reuse one
    Gemini/deterministic client across the LLM arms; non-LLM arms ignore it."""
    code = code.upper()
    if code not in _FACTORIES:
        raise KeyError(f"unknown arm {code!r}; choose from {tuple(_FACTORIES)}")
    factory = _FACTORIES[code]
    if code in NON_LLM:
        return factory()
    return factory(client=client)
