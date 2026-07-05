# Cost & Latency — First-Class Results Plan (C3)

**Owner:** Atishay | **Status:** PLAN — measured in **P4**, reported as a full results subsection.

> **Why this document exists (plain language).** v2 treated cost as an engineering footnote. v3 promotes it to
> a first-class results section (v3 §7.4) because it's the single most useful thing a real SOC team wants:
> *how much does the LLM cost, and is it worth it?* This plan fixes exactly what to measure and how to present
> it, and ties the metrics to the `05` SQLite columns added for this purpose.

---

## 1. What to measure (v3 §7.4)

| Metric | Source (`05` columns) | Notes |
|--------|-----------------------|-------|
| **Filtering ratio per category** | `runs.prefilter_events_in` / `prefilter_events_out` | % of raw events surviving the deterministic pre-filter, per category. A3 (no pre-filter) is the 100% reference. |
| **Cost per scenario per arm** | `runs.token_cost` | Gemini API call count + estimated token cost for A1/A2/A3 and `LCH`. A4/`GD`/`SIGMA` ≈ 0 LLM cost by design. |
| **Latency distribution per arm** | `runs.latency_ms` | Wall-clock ingest→chain-output; report **mean + p95**, per arm, per category. |
| **Cost-vs-accuracy tradeoff** | join `scores.f1`/`recall` with `runs.token_cost` | The efficiency frontier across A1/A2/A3. |

## 2. Key comparisons

- **A2 vs A3** (pre-filter on vs off) → the filtering ratio's effect on **cost, latency, and recall** (this is
  contribution **C3**). A3 should be markedly more expensive than A2; quantify it.
- **A1 vs A2** → does multi-agent decomposition cost more for no accuracy gain? (pairs with H2).
- **LLM arms vs A4/baselines** → the cost premium of the LLM over near-zero-cost rules.

## 3. How it's presented (v3 §7.4)

- A per-category **filtering-ratio table**.
- A per-arm **cost table** (mean token cost / scenario, with seed variance).
- A per-arm **latency table** (mean + p95).
- The headline plot: **F1 (or recall) vs API-cost-per-scenario** across A1/A2/A3 — the practitioner efficiency
  frontier. This is the figure a SOC team will actually use.

## 4. Honesty rules

- Token cost is **measured from API responses**, not assumed (kills the v1 unmeasured "99% filtering" claim).
- Report **per category** — pre-filter behaviour differs sharply (esp. low-and-slow, where the pre-filter may
  discard sparse evidence; cross-link `13` pre-filter recall stress).
- Real-AWS and LocalStack cost/latency reported separately (`environment` column); real-AWS is the headline.
