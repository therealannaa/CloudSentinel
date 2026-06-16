# Mechanical Matching Function — Specification

**Owner:** Anna | 🔒 **FREEZE-FIRST** · ⚠️ **Atishay's Week-3 arms depend on this**
**Status:** DRAFT spec (no implementation). Implemented & unit-tested in Week 2.

> **Why this document exists (plain language).** This is the algorithm that grades the system. It takes what
> an arm *claims* the kill chain was (its reconstructed chain) and the *true* manifest (`03`), and produces an
> exact, reproducible score. Crucially there is **no human judge and no LLM judge** — scoring must be
> deterministic so that anyone re-running the benchmark gets the same numbers. This spec is the counterpart to
> Atishay's manifest schema and must stay consistent with the semantic decisions frozen in `03` §4.

---

## 1. Inputs and output

**Inputs**
- `reconstructed`: an arm's output — an ordered list of detected stages in the **same schema** the manifest
  uses (`stage_id`/order, `ttp_id`, `telemetry_source`, cited `evidence_event_ids`, `timestamp_range`).
- `manifest`: the ground-truth manifest for the scenario (validates against `manifest.schema.json`).

**Output (per scenario)**
- Per-stage `TP / FP / FN` counts.
- Derived: `recall`, `precision`, `f1` (per scenario; later aggregated per **category**, never pooled).
- `order_penalty_applied`: bool/float (see §3).
- Diagnostic list of which ground-truth stages matched / were missed, and which reported stages were spurious.

## 2. What counts as a stage match (TP)

A reported stage `r` matches a ground-truth stage `g` **iff all** hold:

1. **TTP match:** `r.ttp_id == g.ttp_id` (exact). *(Decision to confirm at sync: do we allow parent-technique
   credit, e.g. reported `T1098` for truth `T1098.001`? Default = exact-only; document if relaxed.)*
2. **Evidence binding:** the cited evidence overlaps the truth — `|r.evidence_event_ids ∩ g.evidence_event_ids|
   ≥ 1`. This enforces "right answer, *right reason*" (spec §7.2): a stage with the correct TTP but citing
   unrelated events does **not** earn credit.
3. **Telemetry source match:** `r.telemetry_source == g.telemetry_source`.

Each ground-truth stage may be matched by **at most one** reported stage, and vice-versa (one-to-one;
greedy by `stage_id`). Then:
- **TP** = matched ground-truth stages.
- **FN** = ground-truth stages with no match (missed).
- **FP** = reported stages matching no ground-truth stage (spurious). For **benign** scenarios (`stages: []`)
  *every* reported stage is an FP — this is how FPR is measured.

## 3. Order sensitivity (consistent with `03` §4.1)

**Order matters for full credit.** Partial credit is awarded per matched stage, but a chain recovered out of
order is penalised:

- Compute the matched stages, then check whether their `stage_id` order in `reconstructed` is consistent with
  their order in `manifest` (e.g. via longest-increasing-subsequence over matched stage_ids).
- `order_penalty` is applied to the chain-level score for stages recovered out of sequence. **Fix the exact
  penalty form before any results** (default proposal: report both an *order-agnostic* recall and an
  *order-aware* score, so the penalty choice is transparent and never tuned to flatter an arm).

## 4. Metrics (per scenario → aggregated per category)

```
recall    = TP / (TP + FN)
precision = TP / (TP + FP)          # define precision = 1.0 when an arm reports 0 stages on a benign scenario
f1        = 2 * precision * recall / (precision + recall)   # 0 when precision+recall == 0
```

Aggregation, CIs, effect sizes, and multiplicity correction are governed by `01_pre_registration.md` §4 — the
matching function only emits **per-scenario** raw counts; it does **not** pool categories or pick winners.

## 5. Hard requirements

- **Format parity across A1–A4.** All four arms MUST emit the identical reconstructed-chain schema, or the
  comparison is confounded by output format. The rules-only arm (A4) produces the same structured chain as the
  LLM arms. The matching function rejects malformed output rather than silently scoring it.
- **No LLM/human in scoring.** Pure function of (`reconstructed`, `manifest`).
- **Scores are rankings, not probabilities.** If an arm emits risk scores, treat as rankings unless explicitly
  calibrated — otherwise AUC is meaningless (spec §7.2).
- **Deterministic & total.** Same inputs → same output, always; handles empty `reconstructed` and empty
  `manifest.stages` (benign) without error.

## 6. Reference pseudocode (illustrative only — not the implementation)

```python
def score(reconstructed, manifest):
    gt = manifest["stages"]
    rep = reconstructed["stages"]
    matched_gt, matched_rep = set(), set()

    for i, g in enumerate(gt):
        for j, r in enumerate(rep):
            if j in matched_rep:
                continue
            if (r["ttp_id"] == g["ttp_id"]
                    and r["telemetry_source"] == g["telemetry_source"]
                    and set(r["evidence_event_ids"]) & set(g["evidence_event_ids"])):
                matched_gt.add(i); matched_rep.add(j)
                break

    tp = len(matched_gt)
    fn = len(gt) - tp
    fp = len(rep) - len(matched_rep)

    recall = tp / (tp + fn) if (tp + fn) else 1.0      # benign: no GT stages
    precision = tp / (tp + fp) if (tp + fp) else 1.0   # benign + no reports
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    order_penalty = compute_order_penalty(gt, rep, matched_gt, matched_rep)  # see §3
    return dict(tp=tp, fp=fp, fn=fn, recall=recall, precision=precision,
                f1=f1, order_penalty=order_penalty)
```

## 7. Open decisions for the sync (`07`)

- Exact-TTP-only vs parent-technique credit (§2.1).
- Exact `order_penalty` form (§3).
- Whether evidence binding requires ≥1 overlap (default) or a stricter Jaccard threshold.
