# CloudSentinel / CloudKC-Bench

An open benchmark and controlled study of **LLM cross-domain correlation for AWS multi-stage kill-chain
reconstruction**. **Team:** Atishay & Anna · ISFCR, PES University · Supervisor: Dr. S. Nagasundari ·
**Target venue:** IEEE TIFS / Computers & Security.

Given heterogeneous AWS telemetry (CloudTrail, VPC Flow, S3, EC2) produced during a multi-stage attack,
reconstruct the kill chain — which events belong to the attack, in what order, mapped to which
ATT&CK-for-Cloud techniques — and measure whether an LLM does this **better than fair baselines** (a
single-agent LLM, a no-pre-filter agent, and a deterministic rules-only correlator).

- **Research design (frozen, pre-registered):** [`docs/week1/`](docs/week1/00_README.md) · master plan
  [`docs/RESEARCH_PLAN_v3.md`](docs/RESEARCH_PLAN_v3.md)
- **Paper draft (LaTeX/IEEEtran):** [`paper/`](paper/README.md)
- **CI:** GitHub Actions runs the full suite (581 tests) on py3.11–3.13 on every push.

## Status at a glance

| Phase | What | State |
|-------|------|-------|
| P1 — Freeze design | RQ/H1/H2, power analysis, ~70-scenario taxonomy, manifest schema, matching spec, coverage-gap table | ✅ frozen (`docs/week1/`) |
| P2 — Benchmark generator | simulator (synthetic + real LocalStack), manifests, SQLite cache, held-out sealing, clock model | ✅ complete + tested |
| P3 — Arms + baselines | A1–A4 ablation + community-Sigma baseline; pluggable LLM (deterministic / Ollama / Gemini / OpenAI-compat) | ✅ complete + tested |
| P4 — Analysis | H1/H2 verdicts, bootstrap CIs, effect sizes, Holm-Bonferroni; event-level detection; C4 failure analysis | ✅ complete + tested |
| — First real run | qwen2.5:7b on synthetic telemetry | ▶️ in progress (see [Findings](#current-findings-preliminary)) |
| Ahead | capable-model + real-LocalStack runs, Zeek network telemetry, held-out eval, paper write-up | ⏳ |

> External baselines: **SIGMA (community Sigma rules) is the sole external baseline** — GuardDuty and an
> LLMCloudHunter reimplementation were **dropped** (real-AWS budget not approved / task mismatch), see
> [`docs/week1/11`](docs/week1/11_external_baselines.md).

---

## Install & quick start

```bash
pip install -r requirements-bench.txt      # minimal deps: jsonschema, requests, python-dotenv, pytest
# (requirements.txt is the fuller repo env; boto3 only needed for real LocalStack)

python -m benchmark.cli selfcheck          # runs the WHOLE pipeline in a temp dir -> 10/10 PASS
pytest -q                                  # 581 tests

# generate the benchmark + run the ablation on the deterministic (no-LLM-key) backend:
python -m benchmark.cli run-arms --arms A1,A2,A3,A4 --set dev --seeds 1
python -m benchmark.cli analyze            # H1/H2 verdicts + bootstrap CIs
python -m benchmark.cli detection          # event-level detection (did arms find the attack events?)
python -m benchmark.cli failures           # C4 per-technique miss / false-positive breakdown
```

> **`python` vs `python3`:** use whichever your OS has (`python` on Windows, `python3` on macOS/Linux).

## The `benchmark/` package

```
benchmark/
  events.py         normalized telemetry Event (-> events table)
  manifest.py       Manifest/Stage model + JSON-Schema validation      (docs/week1/03)
  matching.py       mechanical matching fn; ttp_match = exact | parent  (docs/week1/04)
  state_cache.py    SQLite schema + helpers                            (docs/week1/05)
  heldout.py        held-out sealing + tamper detection
  clock_model.py    cross-service delivery-lag measurement             (docs/week1/06)
  runner.py         generate a scenario set end-to-end
  experiment.py     the ablation runner (arms x scenarios x seeds -> scored)
  stats.py          P4: H1/H2, bootstrap CIs, Cohen's dz, permutation p, Holm-Bonferroni, event-level detection
  failure_analysis.py  C4: per-technique misses, FP patterns, pre-filter stress
  tcp_robustness.py    TCP disjoint-stream ΔT-sensitivity robustness test
  analysis.py       per-category aggregation + C3 cost/latency table
  cli.py            command-line entry points
  simulator/
    specs.py            machine-readable mirror of the taxonomy         (docs/week1/02)
    builder.py          deterministic (synthetic) telemetry + manifests
    localstack_backend.py  real boto3 execution against LocalStack (+ real_aws, gated)
  arms/
    signatures.py   event -> candidate TTP detection knowledge
    prefilter.py    deterministic instrumented pre-filter (C3)
    correlate.py    candidates -> reconstructed kill chain (coordinator)
    llm_client.py   pluggable LLM: deterministic | Ollama/OpenAI-compat | Gemini
    arms_impl.py    A1 (multi-agent) / A2 (single) / A3 (raw) / A4 (rules-only)
    sigma.py        community Sigma-rules baseline (SIGMA)
```

## Scenarios & scoring

- **~69 scenarios** across five never-pooled categories — 12 single-domain, 15 multi-stage kill chains,
  12 low-and-slow, 10 ephemeral, 10 benign — **+10 held-out** (sealed). Each cites a real incident + ATT&CK
  technique. The generator emits machine-checkable **manifests** validated against
  [`manifest.schema.json`](docs/week1/manifest.schema.json).
- **Answer-key boundary:** ground truth lives only in `is_ground_truth` + the manifest; the raw event payload
  carries **no** technique label, so arms must infer everything (enforced by tests).
- **Two scoring lenses** (report both):
  - **Technique-level** (`analyze`): a stage matches iff `ttp_id` (`--ttp-match exact|parent`), telemetry
    source, and cited evidence all match. `parent` credits a parent-vs-sub-technique answer.
  - **Event-level** (`detection`): technique-agnostic — did the arm cite the ground-truth *attack events* at
    all? Separates *finding the attack* from *naming the technique*.

## The arms

| Arm | Configuration | Isolates |
|-----|---------------|----------|
| A1 | pre-filter + 4 domain hunters + coordinator | reference (full system) |
| A2 | pre-filter + single generalised agent | A1 vs A2 → multi-agent value (H2) |
| A3 | **no** pre-filter + single agent on raw logs | A2 vs A3 → pre-filter value (C3) |
| A4 | pre-filter + deterministic rules, **no LLM** | A1/A2 vs A4 → LLM value (H1) |
| SIGMA | community CloudTrail+S3 Sigma rules, **no LLM** | external baseline; A4 vs SIGMA shows A4 isn't rigged |

Arms read only arm-visible columns (`event_id`, `source`, `event_time`, `raw_json`) — never `is_ground_truth`.

## Backends

**Telemetry** (both emit the identical schema): `--environment synthetic` (default; deterministic, no infra —
the reproducibility layer) or `--environment localstack` (real boto3 calls; needs `boto3` + `docker compose up`;
`real_aws` is opt-in/gated). Network flows (VPC) are tagged `synthetic_network` since LocalStack emits no flow
logs — Zeek supplies these in the full design.

**LLM** — selection order `LLM_BASE_URL` > `GEMINI_API_KEY` > deterministic:

| Backend | How to select | Notes |
|---------|---------------|-------|
| deterministic (default) | nothing set | signature-based; no key/network; makes the pipeline fully testable |
| **Ollama** (local, free) ⭐ | `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=qwen2.5:7b` | zero cost, no quota, reproducible |
| OpenAI-compatible | `LLM_BASE_URL=…` (Groq / OpenRouter / GitHub Models / Cerebras) | same adapter, hosted models |
| Gemini | `GEMINI_API_KEY=…`, `GEMINI_MODEL=gemini-1.5-flash` | retries rate-limits, aborts cleanly on quota |

The prompt gives the model the **closed 22-technique vocabulary** in scope (not the answer) so the task is
well-posed. Runs are tagged with the real model; `analyze` **warns if a DB mixes models** (use one `--db` per
model/experiment).

### Run with a local model (Ollama)
```bash
# install from https://ollama.com ; then:
ollama pull qwen2.5:7b
export LLM_BASE_URL=http://localhost:11434/v1  LLM_API_KEY=ollama  LLM_MODEL=qwen2.5:7b
python -m benchmark.cli --db qwen.db run-arms --arms A1,A2,A3,A4 --category multi_stage_kill_chain --seeds 3
python -m benchmark.cli --db qwen.db analyze --ttp-match parent
python -m benchmark.cli --db qwen.db detection
```
Convenience runners: `./run_ollama.sh` (macOS/Linux) · `.\run_ollama.ps1` (Windows). RTX 2050 (4 GB): use
`qwen2.5:3b`/`llama3.2:3b` on-GPU; 7B partly offloads to CPU. Full dev run ≈ 1000 local generations — start
with `--category multi_stage_kill_chain` or `--limit`.

## CLI surface

| Command | Purpose |
|---------|---------|
| `generate --set dev\|all` | build scenarios → manifests + events |
| `summary` / `clock` / `seal-heldout` | per-category counts · clock model · seal held-out |
| `selfcheck` | run the whole pipeline in a temp dir (PASS/FAIL) |
| `run-arms --arms … [--category C] [--limit N] [--seeds K] [--environment E]` | run + score the ablation |
| `analyze [--ttp-match stored\|exact\|parent]` | H1/H2 verdicts, bootstrap CIs, effect sizes; mixed-model warning |
| `detection` | technique-agnostic event-level recall/precision |
| `failures [--ttp-match …]` | C4: per-technique miss rates, FP patterns, pre-filter stress |
| `tcp-robustness [--category C] [--dt-min/max/step]` | TCP disjoint-stream stress test with ΔT sensitivity sweep (robustness metric tier) |
| `localstack-check` | is LocalStack reachable? |

## Current findings (preliminary)

First real run: **qwen2.5:7b on synthetic telemetry** (multi-stage category). These are early, single-model,
synthetic-data numbers — not the final result.

- **Technique-level (H1):** A4 rules ≈ 0.91 recall; the LLM arms far lower → **H1 not supported** on synthetic
  data. But note two confounds: exact/parent technique matching, and that `signatures.py` is essentially the
  inverse of the synthetic generator, so rules are near-optimal *by construction*.
- **Event-level (`detection`):** the LLM **finds 0.63–0.77 of attack events at precision 0.92–1.00** on
  multi-stage (and 0.8–0.97 recall on other categories) — *more precise than the rules* (0.73). So the LLM's
  cross-domain **correlation works**; its bottleneck is exact **technique attribution**.
- **H2:** A1 ≈ A2 → multi-agent adds no measurable value (**fail to reject**, as pre-registered).

**Not yet a defensible H1 answer.** That needs (1) a capable model, (2) **real** LocalStack/AWS telemetry
(where rules aren't a perfect inverse), and (3) supervisor sign-off on the primary metric (technique- vs
event-level; exact vs parent). See `docs/week1/15` (threats to validity).

## Repo conventions

- Integration happens on the **`dev`** branch. Generated manifests/DBs are reproducible and git-ignored.
- One `--db <name>.db` per model/experiment to avoid mixing results.
- Glossary of terms: the project study guide (`cloudsentinel_study_guide.md`).
