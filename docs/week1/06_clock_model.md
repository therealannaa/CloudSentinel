# Clock Model — Cross-Service Log Delivery Lag/Skew

**Owner:** Anna
**Status:** TEMPLATE (Week 1). Results table is filled with **measured** values in Week 2.

> **Why this document exists (plain language).** The four telemetry sources do not arrive at the same time.
> Real AWS CloudTrail can take 5–15 minutes to land in S3; VPC Flow uses its own aggregation windows; S3 and
> EC2 differ again. If we claim "event A in CloudTrail and event B in VPC happened close together, so they're
> correlated," that claim is **invalid unless we know the delivery lag between the two sources.** This is a
> *measurement* problem we must solve before any temporal correlation claim — so we measure the lag in our
> LocalStack environment and document it here. (Spec Challenge 2.)

---

## 1. What we measure

For each telemetry source, the difference between:
- **`t_event`** — when the action actually occurred (the simulator's authoritative timestamp), and
- **`t_delivered`** — when the corresponding record became available to our collector / landed in the sink.

`delivery_lag = t_delivered − t_event`. We characterise its distribution (median, p95, max) **per source**,
and the **pairwise skew** between sources (e.g. CloudTrail vs VPC) that matters for correlation windows.

## 2. Method (LocalStack)

1. Run the simulator for a calibration scenario with known action timestamps (`t_event` from the manifest).
2. Poll each collector/sink and record `t_delivered` for every event.
3. Compute `delivery_lag` per event; aggregate per source.
4. Compute pairwise skew = difference in median lag between each source pair.
5. Repeat across ≥ 3 scenarios to estimate variability.

> **Caveat to document:** LocalStack lag is **not** real-AWS lag. The clock model characterises our
> *experimental* environment (which is what the controlled A1–A4 runs use). Real-AWS lag is only relevant to
> the GuardDuty stretch goal and must be reported separately if measured.

## 3. Results table (FILL IN WEEK 2)

| Source | Median lag (s) | p95 lag (s) | Max lag (s) | n events |
|--------|----------------|-------------|-------------|----------|
| CloudTrail | _ | _ | _ | _ |
| VPC Flow | _ | _ | _ | _ |
| S3 | _ | _ | _ | _ |
| EC2 | _ | _ | _ | _ |

### Pairwise skew (median lag difference, seconds)
| Pair | Skew (s) |
|------|----------|
| CloudTrail ↔ VPC | _ |
| CloudTrail ↔ S3 | _ |
| CloudTrail ↔ EC2 | _ |
| VPC ↔ S3 | _ |

## 4. How this feeds the rest of the project

- **Correlation window (ΔT):** the temporal window used to associate events across sources must be chosen
  with reference to the measured skew, and **fixed from external rationale before results** (the TCP
  disjoint-stream robustness test reports ΔT sensitivity — spec §9 / metric tiers).
- **Honest temporal claims:** any "these events are temporally correlated" statement in the paper cites this
  measured model, not an assumption.
