# Phase P1 — Freeze Design (Journal-Tier, v3)

**Project:** CloudKC-Bench — An Open Benchmark and Controlled Study of LLM Cross-Domain Correlation for AWS
Multi-Stage Kill-Chain Reconstruction
**Team:** Atishay & Anna | ISFCR, PES University | **Supervisor:** Dr. S. Nagasundari
**Target venue:** IEEE TIFS / Computers & Security *(confirm with supervisor)*

> **v3 (journal) — changed from v2:** This package was upgraded from the workshop-tier v2 plan to the
> journal-tier v3 plan (`CloudSentinel_Journal_Plan_v3.md`). Scenario count 24 → **~70**; LocalStack → **real
> AWS primary** (LocalStack as reproducibility layer); GuardDuty-only stretch → **3 external baselines**; plus
> new journal-required artifacts: **formal power analysis, coverage-gap table, structured literature review,
> failure-mode analysis, cost/latency as first-class results, inter-rater check.** v2 history is preserved in
> git. The folder name `week1/` is kept (it is now the **P1 design-freeze package**, not a single calendar week).

---

## What Phase P1 is (and why there is still no experiment code)

The project's primary deliverable is a **journal-grade research benchmark**, not just a working system. The
dominant reason security-ML papers are rejected is that measurement decisions were made *after* seeing
results. P1 prevents that by writing down and freezing — in advance — every decision that could later be
massaged: hypotheses, **pre-registered thresholds + a formal power analysis**, the ~70-scenario set, the
ground-truth manifest format, the scoring algorithm, the baselines, and the novelty (coverage-gap) claim.

> **The P1 rule:** no experiment/infrastructure code until these docs are frozen. P1 produces **documents and
> schemas**. The only executable artifacts are the **power-analysis script** (it computes the frozen
> n-per-category) and the schema validator.

Pre-existing repo code (`collectors/`, `tools/`, `config.py`, `docker-compose.yml`, …) remains **Week-2/3
scaffolding**; these freeze docs are the authoritative spec it must conform to.

---

## Deliverables

### P1 freeze package (`docs/week1/`)

| # | File | Owner | Freeze |
|---|------|-------|--------|
| 0 | [00_README.md](00_README.md) (this file) | shared | — |
| 1 | [01_pre_registration.md](01_pre_registration.md) — RQ, H1, H2, thresholds, protocol | **Atishay** (Anna co-signs) | 🔒 |
| 2 | [02_scenario_taxonomy.md](02_scenario_taxonomy.md) — **~70** scenario catalog | Atishay (SD+KC) / Anna (LS,EP,BN,HO) | — |
| 3 | [03_manifest_schema.md](03_manifest_schema.md) + [manifest.schema.json](manifest.schema.json) | **Atishay** | 🔒 ⚠️ |
| 4 | [04_matching_function_spec.md](04_matching_function_spec.md) | **Anna** | 🔒 ⚠️ |
| 5 | [05_sqlite_state_cache_schema.md](05_sqlite_state_cache_schema.md) | **Atishay** | — |
| 6 | [06_clock_model.md](06_clock_model.md) — dual-environment | **Anna** | — |
| 7 | [07_sync_checkpoint_agenda.md](07_sync_checkpoint_agenda.md) | shared | — |
| 8 | [08_power_analysis.md](08_power_analysis.md) + [power_analysis.py](power_analysis.py) — **NEW** | **Atishay** | 🔒 |
| 9 | [09_coverage_gap_table.md](09_coverage_gap_table.md) — **NEW** (C1 novelty) | Anna | — |
| 10 | [10_real_aws_setup.md](10_real_aws_setup.md) — **NEW** (budget-gated) | shared | — |
| 11 | [11_external_baselines.md](11_external_baselines.md) — **NEW** (3 baselines) | Anna | — |
| 12 | [12_literature_review.md](12_literature_review.md) — **NEW** (25–30 papers) | Anna | — |
| 13 | [13_failure_mode_analysis_plan.md](13_failure_mode_analysis_plan.md) — **NEW** (C4, run in P4/P5) | shared | — |
| 14 | [14_cost_latency_plan.md](14_cost_latency_plan.md) — **NEW** (C3 results) | Atishay | — |
| 15 | [15_threats_to_validity.md](15_threats_to_validity.md) — **NEW** | shared | — |

**Master roadmap:** [../RESEARCH_PLAN_v3.md](../RESEARCH_PLAN_v3.md) — P1–P5 phases, owners, dates, gating, DoD.

**Legend:** 🔒 freeze-first · ⚠️ blocking dependency for the other person.

---

## Definition of Done — P1 (journal, v3 §13 subset due in P1)

- [ ] Pre-registration signed + dated (`01`).
- [ ] **Formal power analysis written and frozen** (`08`); short categories flagged descriptive-only.
- [ ] Manifest schema merged (`03` + `manifest.schema.json`).
- [ ] Matching-function spec merged (`04`).
- [ ] **~70 scenarios + held-out authored** with real-incident grounding (`02`); held-out marked for sealing.
- [ ] **Inter-rater check** process defined; ≥20% of scenarios slated for independent review (`02`).
- [ ] **Coverage-gap table** structure in place; competitor cells flagged "read the paper" (`09`).
- [ ] External-baselines spec merged (`11`); literature-review skeleton merged (`12`).
- [ ] Real-AWS setup + **budget estimate** drafted for supervisor sign-off (`10`).
- [ ] Sync checkpoint held; venue / budget / LLMCloudHunter-scope decisions logged (`07`).

The full 12-item *paper-submittable* DoD lives in [../RESEARCH_PLAN_v3.md](../RESEARCH_PLAN_v3.md) (§13).

## Glossary
See the project study guide (`cloudsentinel_study_guide.md`), "Quick Reference: Key Terms".
