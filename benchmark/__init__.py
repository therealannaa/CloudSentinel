"""
CloudKC-Bench — benchmark generator and scoring (Phase P2).

This package implements the P2 ("Environment + Benchmark Generator") deliverables
defined in docs/week1/ (the frozen P1 design):

  - state_cache : the SQLite shared state cache (docs/week1/05)
  - manifest    : the ground-truth manifest model + JSON-Schema validation (docs/week1/03)
  - matching    : the mechanical matching function (docs/week1/04)
  - simulator   : the attack_simulator that emits telemetry + manifests for all
                  ~69 scenarios in the taxonomy (docs/week1/02)
  - heldout     : sealing of the held-out validation set
  - clock_model : cross-service delivery-lag measurement (docs/week1/06)

Design note: the simulator has two backends. The default ``synthetic`` backend
generates deterministic telemetry with no external dependency (the reproducibility
layer — runnable on a laptop/CI). The optional ``localstack`` backend fires real
boto3 calls against ``docker compose up`` LocalStack to capture real telemetry.
Both emit the identical event + manifest schema.
"""

__all__ = [
    "events",
    "manifest",
    "matching",
    "state_cache",
    "simulator",
    "heldout",
    "clock_model",
]
