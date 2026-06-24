# CloudSentinel / CloudKC-Bench

An open benchmark and controlled study of LLM cross-domain correlation for AWS multi-stage kill-chain
reconstruction. **Team:** Atishay & Anna · ISFCR, PES University · Supervisor: Dr. S. Nagasundari.

The frozen research design (P1) lives in [`docs/week1/`](docs/week1/00_README.md); the master plan is
[`docs/RESEARCH_PLAN_v3.md`](docs/RESEARCH_PLAN_v3.md).

---

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

## Phase P2 — Benchmark generator (`benchmark/`)

The `benchmark/` package generates all ~69 taxonomy scenarios as telemetry + machine-checkable ground-truth
manifests, ingests them into the SQLite state cache, scores reconstructed chains, seals the held-out set, and
measures the clock model.

```
benchmark/
  events.py        normalized telemetry Event (-> events table)
  manifest.py      Manifest/Stage model + JSON-Schema validation (docs/week1/03)
  matching.py      mechanical matching function (docs/week1/04)
  state_cache.py   SQLite schema + helpers (docs/week1/05)
  heldout.py       held-out sealing + tamper detection
  clock_model.py   cross-service delivery-lag measurement (docs/week1/06)
  runner.py        generate a scenario set end-to-end
  experiment.py    P3 ablation runner (A1-A4 x scenarios x seeds -> scored)
  analysis.py      per-category aggregation + C3 cost/latency table
  cli.py           command-line entry points
  simulator/
    specs.py       machine-readable mirror of the taxonomy (docs/week1/02)
    builder.py     deterministic telemetry + manifest generator
  arms/            the four ablation arms (P3)
    signatures.py  event -> candidate TTP detection knowledge
    prefilter.py   deterministic instrumented pre-filter (C3)
    correlate.py   candidates -> reconstructed kill chain (coordinator)
    llm_client.py  pluggable LLM backend (deterministic offline | Gemini)
    arms_impl.py   A1 (multi-agent) / A2 (single) / A3 (raw) / A4 (rules-only)
```

### Quick start

```bash
pip install -r requirements.txt          # adds jsonschema

python3 -m benchmark.cli selfcheck         # run the WHOLE pipeline, report PASS/FAIL

./run_scenarios.sh dev                    # 59 dev scenarios -> manifests + events
./run_scenarios.sh all                    # dev + held-out, then seal held-out

# or the CLI directly:
python3 -m benchmark.cli generate --set all
python3 -m benchmark.cli summary
python3 -m benchmark.cli seal-heldout
python3 -m benchmark.cli clock --set dev

# P3 — run the four-arm ablation and score it
python3 -m benchmark.cli run-arms --arms A1,A2,A3,A4 --set dev --seeds 3 --csv results.csv

pytest                                    # 521 tests (P1-P3 + backends)
```

`selfcheck` generates all 69 scenarios in a throwaway workspace and verifies
generate → validate → ingest → seal → **score** → clock end-to-end (10/10 checks).

### Environment (LocalStack + MinIO)

```bash
docker compose up -d                      # LocalStack (AWS APIs) + MinIO (S3 sink)
```

### Backends

The simulator has two backends, both emitting the identical event + manifest schema:

- **`synthetic`** (default) — deterministic telemetry, no external dependency. The reproducibility layer;
  runs on a laptop / CI.
- **`localstack`** — fires **real boto3 calls** against LocalStack (resources really created/read/deleted)
  and captures the responses as telemetry (`benchmark/simulator/localstack_backend.py`). Needs `boto3` +
  `docker compose up`. Real AWS is budget-gated (`docs/week1/10`).

```bash
docker compose up -d
pip install boto3
python3 -m benchmark.cli localstack-check                     # REACHABLE?
ENVIRONMENT=localstack ./run_scenarios.sh dev                # capture REAL telemetry
python3 -m benchmark.cli run-arms --environment localstack    # score arms on it
```

> Honest scope: LocalStack community CloudTrail history is limited, so we capture the calls we issue
> (what a collector at the API boundary sees) + resource state. Console-login and IMDS steps are proxied with
> `sts:GetCallerIdentity` (tagged `proxy`); VPC Flow Logs aren't produced by LocalStack, so network events are
> tagged `synthetic_network` (Zeek supplies these in the full design). The backend's logic is unit-tested
> offline with a fake boto3 (`tests/test_localstack_backend.py`); run the commands above on a networked host
> to capture live.

### Real LLM (Gemini)

A1–A3 use a deterministic offline backend by default. Provide a key to switch to real Gemini — no code change:

```bash
pip install google-generativeai
export GEMINI_API_KEY=...          # GEMINI_MODEL pins the version
python3 -m benchmark.cli run-arms --arms A1,A2,A3,A4 --set dev --seeds 3
# -> "LLM backend: gemini"; A1/A2/A3 now reason over raw telemetry (real H1/H2 signal)
```

The prompt/parse path is unit-tested offline with a mocked client (`tests/test_llm_backend.py`).

### What P2 delivers (Definition of Done)

- `docker-compose.yml` brings up LocalStack + MinIO (environment layer).
- `./run_scenarios.sh dev` produces all 59 dev manifests, every one schema-valid.
- Matching function implemented + unit-tested (`tests/test_benchmark_matching.py`).
- Held-out set sealed with checksum lock; tamper-detected (`benchmark/heldout.py`).
- Clock model measured (synthetic now; LocalStack/real-AWS per `docs/week1/06`).

Generated manifests/DB are reproducible and git-ignored; regenerate with `run_scenarios.sh`.

---

## Phase P3 — Four-arm ablation (`benchmark/arms/`)

`run-arms` runs A1–A4 over a scenario set across seeds, scores each reconstruction with the matching function,
and writes `runs` / `reconstructed_stages` / `scores` to the state cache, plus a per-category results table.

| Arm | Configuration | Isolates |
|-----|---------------|----------|
| A1 | pre-filter + 4 domain hunters + coordinator | reference (full system) |
| A2 | pre-filter + single generalised agent | A1 vs A2 → multi-agent value (H2) |
| A3 | **no** pre-filter + single agent on raw logs | A2 vs A3 → pre-filter value (C3) |
| A4 | pre-filter + deterministic rules, **no LLM** | A1/A2 vs A4 → LLM value (H1) |

**LLM backend.** A1–A3 use a pluggable client: the **deterministic** offline backend (default — runs with no
API key, so the whole ablation is testable) or **Gemini** (auto-selected when `GEMINI_API_KEY` is set). A4 is
pure rules. The arms read only arm-visible columns (`event_id`, `source`, `event_time`, `raw_json`) — never
`is_ground_truth` (the answer-key boundary, enforced by `ArmEvent` and tests).

> **Honest status.** The full P3 machinery — pre-filter (instrumented), A4 rules, the four arms, the runner,
> scoring, multi-seed, per-category analysis with C3 cost/latency — is complete and tested (`run-arms` scores
> 708 runs on the dev set). With the **deterministic** backend the LLM arms (A1/A2/A3) detect identically to
> A4 and differ only in cost/latency, so **comparative H1/H2 numbers are NOT meaningful yet** — they require
> (a) a real LLM via `GEMINI_API_KEY` and (b) real telemetry (LocalStack/real-AWS). The pipeline is ready to
> produce real results the moment those two inputs are supplied.

### Still ahead (P3 completion → P4)
A first **live run** (LocalStack telemetry + `GEMINI_API_KEY`) to get real H1/H2 numbers — both paths are
wired and offline-tested, they just need network + a key. Then: Zeek for real VPC-flow telemetry; the external
baselines (GuardDuty, LLMCloudHunter reimpl, community Sigma — `docs/week1/11`); and P4 statistics (bootstrap
CIs, Holm-Bonferroni, effect sizes per `docs/week1/08`).
