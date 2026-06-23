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
  cli.py           command-line entry points
  simulator/
    specs.py       machine-readable mirror of the taxonomy (docs/week1/02)
    builder.py     deterministic telemetry + manifest generator
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

pytest                                    # 195 tests (matching, manifests, pipeline)
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
