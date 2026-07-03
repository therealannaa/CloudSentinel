"""TCP disjoint-stream / ΔT sensitivity test — DoD item 11.

Background
----------
``correlate.build_chain`` assigns stage_id order by sorting candidates on
``event_time``.  In the benchmark each telemetry source is an independent
"stream" whose events carry timestamps that may be offset from the true action
time by a source-specific delivery lag (CloudTrail ~7 min, VPC ~75 s, EC2 ~30 s
— see ``clock_model.SYNTHETIC_LAG_SECONDS``).

When one source's events are shifted by ΔT seconds relative to the others, the
temporal ordering seen by the correlator diverges from the ground-truth stage
order in the manifest.  This raises ``order_penalty`` and reduces
``order_aware_recall`` — the metric that captures both detection *and* ordering
correctness.

What this module does
---------------------
For a given scenario and a chosen source to perturb:

1. Build *perfect* candidates from the manifest (one Candidate per evidence
   event; timestamps taken from ``stage.timestamp_range[0]``).
2. Sweep ΔT over a configurable range of integer offsets (seconds).
3. For each ΔT, shift the ``event_time`` of every candidate whose
   ``telemetry_source == perturbed_source`` by ΔT seconds.
4. Re-run ``correlate.build_chain`` on the shifted candidates.
5. Score against the manifest → record recall, order_penalty, order_aware_recall.
6. Return the full sweep table.

Interpretation
--------------
- At ΔT = 0, a perfect arm yields order_penalty = 0 and order_aware_recall = 1.0
  (assuming ground-truth events are already in strictly-increasing timestamp order,
  which the synthetic generator guarantees).
- The *robustness threshold* is the minimum |ΔT| at which order_penalty > 0: the
  maximum delivery-lag difference the correlator tolerates without misordering.
- Reporting this threshold alongside the clock-model skews (docs/week1/06)
  justifies the ΔT design choice and fulfils the "TCP disjoint-stream" DoD item.
- Crucially, ``recall`` is invariant to ΔT: the matching function does not use
  timestamps, only (ttp_id, telemetry_source, evidence_event_ids).  A rising
  order_penalty at fixed recall is a *pure ordering* failure, not a detection
  failure.
"""
from __future__ import annotations

import csv
import dataclasses
from datetime import datetime, timezone, timedelta
from itertools import groupby
from typing import Iterable, Sequence

from benchmark.arms.base import Candidate
from benchmark.arms import correlate
from benchmark.matching import score


@dataclasses.dataclass
class DeltaResult:
    scenario_id: str
    perturbed_source: str
    delta_t_seconds: int
    recall: float
    order_penalty: float
    order_aware_recall: float


def _parse_ts(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _shift_ts(ts: str, delta_seconds: int) -> str:
    return (_parse_ts(ts) + timedelta(seconds=delta_seconds)).isoformat()


def candidates_from_manifest(manifest_dict: dict) -> list[Candidate]:
    """Build a *perfect* candidate list from a manifest.

    One Candidate per evidence_event_id; ``event_time`` taken from
    ``stage.timestamp_range[0]``.  Running these through ``build_chain`` at
    ΔT=0 reproduces the ground-truth stage order exactly (provided the generator
    assigned strictly-increasing timestamps per stage, which it does).
    """
    cands: list[Candidate] = []
    for stage in manifest_dict.get("stages", []):
        ts = stage["timestamp_range"][0]
        for eid in stage["evidence_event_ids"]:
            cands.append(Candidate(
                event_id=eid,
                telemetry_source=stage["telemetry_source"],
                ttp_id=stage["ttp_id"],
                event_time=ts,
            ))
    return cands


def sweep(
    scenario_id: str,
    manifest_dict: dict,
    perturbed_source: str,
    delta_t_range: Sequence[int],
) -> list[DeltaResult]:
    """Sweep ΔT for one (scenario, source) pair and return per-ΔT scores."""
    base_cands = candidates_from_manifest(manifest_dict)
    results: list[DeltaResult] = []
    for dt in delta_t_range:
        shifted = [
            dataclasses.replace(c, event_time=_shift_ts(c.event_time, dt))
            if c.telemetry_source == perturbed_source else c
            for c in base_cands
        ]
        chain = correlate.build_chain(shifted)
        s = score(chain, manifest_dict)
        results.append(DeltaResult(
            scenario_id=scenario_id,
            perturbed_source=perturbed_source,
            delta_t_seconds=dt,
            recall=s.recall,
            order_penalty=s.order_penalty,
            order_aware_recall=s.order_aware_recall,
        ))
    return results


# Default ΔT sweep: covers the full range of synthetic delivery lags from
# clock_model.SYNTHETIC_LAG_SECONDS (max = CloudTrail at 420 s) with extra
# headroom, at a step fine enough to locate the exact robustness threshold.
DEFAULT_DT_RANGE = list(range(-900, 901, 60))


def run_all(
    scenarios: dict[str, dict],
    delta_t_range: Sequence[int] | None = None,
    sources: list[str] | None = None,
) -> list[DeltaResult]:
    """Run the ΔT sweep over all scenarios × sources.

    Only perturbs sources that actually appear in the scenario's stages (so
    single-source scenarios aren't tested for inter-source ordering, which
    is meaningless for them).
    """
    dt_range = delta_t_range if delta_t_range is not None else DEFAULT_DT_RANGE
    sources_to_test = sources or ["CloudTrail", "S3", "VPC", "EC2"]

    all_results: list[DeltaResult] = []
    for sid, manifest in scenarios.items():
        present = {s["telemetry_source"] for s in manifest.get("stages", [])}
        for source in sources_to_test:
            if source in present:
                all_results.extend(sweep(sid, manifest, source, dt_range))
    return all_results


def robustness_threshold(results: list[DeltaResult]) -> dict[tuple[str, str], int | None]:
    """Return the minimum |ΔT| (seconds) at which order_penalty > 0 per (scenario, source).

    A value of ``None`` means no degradation was observed across the entire sweep.
    """
    thresholds: dict[tuple[str, str], int | None] = {}
    key_fn = lambda r: (r.scenario_id, r.perturbed_source)
    for k, group in groupby(sorted(results, key=key_fn), key=key_fn):
        ordered = sorted(group, key=lambda r: abs(r.delta_t_seconds))
        thresh: int | None = None
        for r in ordered:
            if r.order_penalty > 0:
                thresh = abs(r.delta_t_seconds)
                break
        thresholds[k] = thresh
    return thresholds


def print_report(results: list[DeltaResult], max_rows: int = 100) -> None:
    """Print a compact sweep table (truncated to max_rows for readability)."""
    hdr = f"{'scenario':<12}{'source':<14}{'ΔT(s)':>8}{'recall':>8}{'penalty':>10}{'oar':>8}"
    print(hdr)
    print("-" * len(hdr))
    shown = 0
    for r in results:
        if shown >= max_rows:
            print(f"  ... ({len(results) - max_rows} more rows; use --csv to export all)")
            break
        print(f"{r.scenario_id:<12}{r.perturbed_source:<14}{r.delta_t_seconds:>8}"
              f"{r.recall:>8.3f}{r.order_penalty:>10.3f}{r.order_aware_recall:>8.3f}")
        shown += 1


def to_csv(results: list[DeltaResult], path: str) -> None:
    fields = ["scenario_id", "perturbed_source", "delta_t_seconds",
              "recall", "order_penalty", "order_aware_recall"]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(dataclasses.asdict(r) for r in results)
