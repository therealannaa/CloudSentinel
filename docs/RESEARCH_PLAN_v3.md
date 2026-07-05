# CloudKC-Bench — Master Research Plan (v3, Journal-Tier)

**Project:** An Open Benchmark and Controlled Study of LLM Cross-Domain Correlation for AWS Multi-Stage
Kill-Chain Reconstruction
**Team:** Atishay & Anna | ISFCR, PES University | **Supervisor:** Dr. S. Nagasundari
**Target venue:** IEEE TIFS / Computers & Security *(confirm — `docs/week1/07` §8)*
**Supersedes:** v2 workshop plan (`research.md`). Source: `CloudSentinel_Journal_Plan_v3.md`.

> This is the single "going-forward" plan. Phase P1 (design freeze) is operationalised by the package in
> [`docs/week1/`](week1/00_README.md) (folder name kept for git continuity; it is the P1 freeze package).

---

## Vision

Release an open, ground-truthed benchmark of multi-stage AWS control-plane attacks and use it — under a
controlled four-arm ablation with fair external baselines — to measure *when and whether* an LLM
cross-domain correlation layer improves kill-chain reconstruction over single-agent and rules-only detection.
Report honest results either way. The benchmark stands as a contribution even if the system does not "win."

## Contributions (journal)
C1 open AWS kill-chain benchmark · C2 controlled four-arm ablation · C3 cost/latency tradeoff (first-class) ·
C4 failure-mode taxonomy · C5 reproducibility artifact. (Details: `CloudSentinel_Journal_Plan_v3.md` §3.)

## Operating principles (every phase)
- **LocalStack-first, real-AWS-gated:** build & validate on LocalStack (no cost, not blocked). Real AWS is the
  primary *reporting* environment but only starts once the budget is approved (`docs/week1/10`, `07` §9).
- Per-category, never pooled · scenario = unit of analysis · seeds vary · enrichers disabled ·
  held-out sealed before finalisation · pre-registered thresholds + frozen power analysis.

---

## Phases (dates to fill with supervisor; ~16-week skeleton)

| Phase | Focus | Key tasks | Owner | Target |
|-------|-------|-----------|-------|--------|
| **P1 · Freeze** | Pre-registration + benchmark spec + power analysis | Lock RQ/H1/H2 + thresholds; **freeze power analysis** (`08`); author **~70 scenarios** w/ grounding (`02`); publish manifest schema (`03`) + matching fn (`04`); **coverage-gap table** structure (`09`); baselines spec (`11`); lit-review skeleton (`12`); real-AWS setup + **budget** (`10`); supervisor sign-off (`07`). | Shared | **[~Wk 1–2]** |
| **P2 · Env + Benchmark** | LocalStack env + scenario generator (+ real-AWS on budget) | LocalStack/MinIO/Zeek/Docker up; `attack_simulator` emits all scenarios + manifests; collectors → SQLite (`05`); **freeze held-out set**; **inter-rater check on ≥20%**; clock model — LocalStack now, real-AWS on approval (`06`). | Anna (infra) / Atishay (scenarios) | **[~Wk 3–6]** |
| **P3 · Arms + Baselines** | 4 arms + 1 external baseline | A1 (hunters+coordinator), A2 (single agent), A3 (raw-log), A4 (rules + **community Sigma**); pre-filter instrumentation for cost/latency (`14`). GuardDuty and LLMCloudHunter **dropped** (see `11_external_baselines.md`). | Atishay (A1, A4, pre-filter) / Anna (collectors, A2/A3) | **DONE** ✅ |
| **P4 · Core Experiment** | Run everything; measure | Multi-seed runs on LocalStack (repro) + real AWS (primary); primary metrics + TCP stress test; **cost/latency** (`14`); scenario-level + per-category stats with bootstrap CIs + Holm-Bonferroni over the **2 primary tests** (`08`). | Shared | **[~Wk 9–12]** |
| **P5 · Analysis + Write-up** | Failure-mode analysis + paper | **Failure-mode analysis** (`13`); Abstract/System/Results/Failure/Limitations (Atishay); Intro/Related-Work/Discussion/Conclusion (Anna); release CloudKC-Bench + **DOI**; reproducibility README (real-AWS + LocalStack). | Split | **[~Wk 12–16]** |
| **STRETCH** | Extended real-AWS coverage | If on schedule, expand real-AWS runs from subset to full set. | Shared | conditional |

## Critical dependencies (do these in order)
1. **Power analysis `08` → pre-registration `01`** — the H1 margin must be detectable at the frozen n; freeze before any run.
2. **Manifest schema `03` + SQLite schema `05` → Anna's P2 collectors** (⚠️ blocking).
3. **Matching-fn spec `04` → Atishay's P3 arms** (⚠️ blocking). GuardDuty/LLMCloudHunter adapters dropped; only SIGMA adapter needed (done).
4. **Supervisor budget `07` §9 → real-AWS provisioning `10`** (everything else stays on LocalStack).
5. **Failure-mode data capture (`13` §2) must be wired into the P3/P4 runner** or C4 is impossible later.

## Definition of Done — paper submittable (v3 §13, 12 items)
1. CloudKC-Bench released (generator, manifests, schema, matching fn, held-out, DOI, repro README — real-AWS + LocalStack).
2. A1–A4 run on real AWS (primary) + LocalStack (repro) with multi-seed variance.
3. External baseline (community Sigma / SIGMA arm) run on the full benchmark. GuardDuty dropped (budget-gated, no real-AWS approval). LLMCloudHunter dropped (task mismatch — rule generation ≠ kill-chain reconstruction; positioned in related work). See `11_external_baselines.md`.
4. Formal power analysis in paper; sub-threshold categories flagged descriptive-only.
5. Primary metrics per category with effect sizes, bootstrap CIs, Holm-Bonferroni.
6. H1 and H2 each explicitly supported or refuted.
7. Cost/latency section complete (filtering ratios, per-arm cost, tradeoff curve).
8. Failure-mode analysis complete (per-category, per-technique, LLM-specific).
9. Literature review covers 25–30 papers in a structured taxonomy.
10. Coverage-gap table complete with paper-verified entries.
11. TCP disjoint-stream robustness test with ΔT sensitivity. **DONE** ✅ (`benchmark/tcp_robustness.py`; `benchmark.cli tcp-robustness`; 17 tests in `tests/test_tcp_robustness.py`).
12. All citations traced to locatable sources.

## Supervisor decisions blocking P2 (`docs/week1/07`)
Venue (§8) · **real-AWS budget (§9)** · LLMCloudHunter scope partial/full (§10) · journal-scope sign-off (§11).

## Honest standing limitations (state in paper — v3 §15)
Synthetic-scenario ceiling · single-group validation · LLM temporal drift · **category-level statistical
power limited to very-large effects after correction** (`08`) · adversarial LLM evasion excluded.
