"""Clock model — cross-service delivery lag/skew measurement (docs/week1/06).

In the synthetic backend we model realistic per-source delivery lag (CloudTrail's
5-15 min S3 delivery, VPC Flow aggregation windows, etc.) so the temporal-
correlation machinery can be exercised offline. On LocalStack/real-AWS the same
function consumes measured (t_event, t_delivered) pairs.
"""
from __future__ import annotations

import statistics

# Modelled delivery lag (seconds) per source for the synthetic backend. These are
# placeholders that mimic real-AWS characteristics; real measured values replace
# them in P2 (LocalStack) and on budget-approval (real AWS) — see docs/week1/06.
SYNTHETIC_LAG_SECONDS = {
    "CloudTrail": 420,   # ~7 min (real CloudTrail S3 delivery 5-15 min)
    "VPC": 75,           # aggregation window
    "S3": 130,
    "EC2": 30,
}


def synthetic_pairs(events):
    """Attach a modelled delivery lag to each event -> (source, lag) pairs."""
    return [(e.source, SYNTHETIC_LAG_SECONDS.get(e.source, 60)) for e in events]


def summarize(pairs):
    """pairs: iterable of (source, lag_seconds). Returns per-source stats +
    pairwise skew (difference of medians), matching the docs/week1/06 tables."""
    by_source: dict[str, list[float]] = {}
    for source, lag in pairs:
        by_source.setdefault(source, []).append(float(lag))

    per_source = {}
    for source, lags in sorted(by_source.items()):
        lags_sorted = sorted(lags)
        per_source[source] = {
            "median": statistics.median(lags_sorted),
            "p95": lags_sorted[min(len(lags_sorted) - 1, int(0.95 * (len(lags_sorted) - 1)))],
            "max": max(lags_sorted),
            "n": len(lags_sorted),
        }

    sources = list(per_source)
    skew = {}
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            a, b = sources[i], sources[j]
            skew[f"{a}<->{b}"] = abs(per_source[a]["median"] - per_source[b]["median"])
    return {"per_source": per_source, "pairwise_skew": skew}
