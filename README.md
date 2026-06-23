# CloudSentinel / CloudKC-Bench

An open benchmark and controlled study of LLM cross-domain correlation for AWS multi-stage kill-chain
reconstruction. **Team:** Atishay & Anna · ISFCR, PES University · Supervisor: Dr. S. Nagasundari.

The frozen research design (P1) lives in [`docs/week1/`](docs/week1/00_README.md); the master plan is
[`docs/RESEARCH_PLAN_v3.md`](docs/RESEARCH_PLAN_v3.md).

---

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

python -m benchmark.cli selfcheck         # run the WHOLE pipeline, report PASS/FAIL

./run_scenarios.sh dev                    # 59 dev scenarios -> manifests + events
./run_scenarios.sh all                    # dev + held-out, then seal held-out

# or the CLI directly:
python -m benchmark.cli generate --set all
python -m benchmark.cli summary
python -m benchmark.cli seal-heldout
python -m benchmark.cli clock --set dev

# P3 — run the four-arm ablation and score it
python -m benchmark.cli run-arms --arms A1,A2,A3,A4 --set dev --seeds 3 --csv results.csv

pytest                                    # 365 tests (P2 + P3)
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
- **`localstack`** / **`real_aws`** — fire real API calls and capture real CloudTrail/VPC/S3/EC2 telemetry
  (`docker compose up` for LocalStack; real AWS is budget-gated, see `docs/week1/10`). *Interface in place;
  real-telemetry capture is wired in P2/P3.*

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
Real-LocalStack telemetry capture (boto3 + collector→`events` wiring + Zeek); external baselines (GuardDuty,
LLMCloudHunter reimpl, community Sigma — `docs/week1/11`); then P4 statistics (bootstrap CIs, Holm-Bonferroni,
effect sizes per `docs/week1/08`).
