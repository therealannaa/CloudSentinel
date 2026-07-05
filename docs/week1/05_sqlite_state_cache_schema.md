# SQLite State-Cache Schema — CloudKC-Bench

**Owner:** Atishay
**Status:** DRAFT design for P1 freeze. Tables created in code in P2.

> **v3 (journal) — changed from v2:** added `environment` (`real_aws`/`localstack`) for the dual-environment
> design; broadened `runs.arm` to include the 3 external baselines (`GD`, `LCH`, `SIGMA`); added cost/latency
> columns (`latency_ms`, `prefilter_events_in`, `prefilter_events_out`) feeding the C3 first-class results
> (`14_cost_latency_plan.md`); added `author`/`reviewer` to `scenarios` (inter-rater check).

> **Why this document exists (plain language).** SQLite is a database that lives in a single file
> (`cloudsentinel.db`). It is the shared "memory" that ties the whole pipeline together: collectors write
> normalized log events into it, the pre-filter marks which events passed, the arms read events and write
> back their reconstructed chains, and we record every run/seed so multi-seed variance is reproducible.
> Designing the tables **now** gives Week-2 code a fixed target and guarantees the schema supports the
> evaluation protocol (especially "unit = scenario" and "seeds are repeated measures").

---

## 1. Relationship to existing tables

The repo already defines some tables (see `docs/schemas.md`): `ec2_instances` (ec2_collector), and the
baseline/tools tables `instances_baseline`, `ip_history`, `access_patterns`, `alerts`, `mitre_techniques`.
Those are **kept**. This document adds the **benchmark state-cache** tables needed for the four-arm
experiment. All live in the same `cloudsentinel.db` (path from `DB_PATH` in `config.py`).

| Table | New / existing | Purpose |
|-------|----------------|---------|
| `scenarios` | new | One row per benchmark scenario (mirrors the manifest catalog). |
| `events` | new | Normalized log events per scenario, with pre-filter decision. |
| `runs` | new | One row per (arm × scenario × seed) execution. |
| `reconstructed_stages` | new | Stages an arm reconstructed for a run (the scored output). |
| `agent_outputs` | new | Raw per-agent JSON output (provenance/debugging). |
| `scores` | new | Per-run matching-function results (TP/FP/FN, recall, precision, f1). |
| `mitre_techniques` | existing | ATT&CK reference (from `tools/mitre_lookup.py`). |

## 2. DDL (illustrative; finalised in Week-2 code)

```sql
-- One row per scenario; the dev/held-out catalog from 02_scenario_taxonomy.md
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id   TEXT PRIMARY KEY,                 -- e.g. 'KC-02'
    category      TEXT NOT NULL,                    -- single_domain | multi_stage_kill_chain | ...
    is_held_out   INTEGER NOT NULL DEFAULT 0,       -- 1 = sealed held-out set
    manifest_path TEXT,                             -- path to the ground-truth manifest JSON
    author        TEXT,                             -- scenario author (inter-rater check)
    reviewer      TEXT,                             -- independent reviewer, or NULL
    created_at    TEXT NOT NULL
);

-- Normalized telemetry events captured per scenario run of the simulator
CREATE TABLE IF NOT EXISTS events (
    event_id          TEXT PRIMARY KEY,             -- stable id used in manifest evidence_event_ids
    scenario_id       TEXT NOT NULL REFERENCES scenarios(scenario_id),
    environment       TEXT NOT NULL DEFAULT 'localstack', -- real_aws | localstack (dual-env)
    source            TEXT NOT NULL,                -- CloudTrail | VPC | S3 | EC2
    event_time        TEXT NOT NULL,               -- ISO-8601 UTC
    raw_json          TEXT NOT NULL,               -- original event payload
    normalized_json   TEXT,                         -- normalized fields (shared schema)
    pre_filter_passed INTEGER NOT NULL DEFAULT 0,  -- 1 if the deterministic pre-filter kept it
    is_ground_truth   INTEGER NOT NULL DEFAULT 0   -- 1 if this event belongs to a manifest stage
);

-- One row per (arm, scenario, seed, environment) execution
CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,           -- uuid
    arm                 TEXT NOT NULL,              -- A1 | A2 | A3 | A4 | GD | LCH | SIGMA
    environment         TEXT NOT NULL,              -- real_aws | localstack
    scenario_id         TEXT NOT NULL REFERENCES scenarios(scenario_id),
    seed                INTEGER NOT NULL,           -- repeated-measure index (>=3 per LLM arm)
    model_version       TEXT,                       -- pinned model id+date (held fixed across LLM arms)
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    latency_ms          INTEGER,                    -- wall-clock ingest->output (C3 latency)
    token_cost          INTEGER,                    -- token/API spend (C3 cost; ~0 for A4/GD/SIGMA)
    prefilter_events_in  INTEGER,                   -- events before pre-filter (C3 filtering ratio)
    prefilter_events_out INTEGER,                   -- events after pre-filter
    UNIQUE (arm, scenario_id, seed, environment)
);

-- The reconstructed kill chain an arm produced (the scored output)
CREATE TABLE IF NOT EXISTS reconstructed_stages (
    run_id             TEXT NOT NULL REFERENCES runs(run_id),
    stage_id           INTEGER NOT NULL,
    ttp_id             TEXT NOT NULL,
    telemetry_source   TEXT NOT NULL,
    evidence_event_ids TEXT NOT NULL,               -- JSON array of event_id
    t_start            TEXT,
    t_end              TEXT,
    PRIMARY KEY (run_id, stage_id)
);

-- Raw per-agent output for provenance/debugging (A1 hunters + coordinator)
CREATE TABLE IF NOT EXISTS agent_outputs (
    run_id      TEXT NOT NULL REFERENCES runs(run_id),
    agent_id    TEXT NOT NULL,                      -- identity_hunter | network_hunter | ... | coordinator
    output_json TEXT NOT NULL,
    PRIMARY KEY (run_id, agent_id)
);

-- Matching-function result per run (raw counts; aggregation happens in analysis, never here)
CREATE TABLE IF NOT EXISTS scores (
    run_id        TEXT PRIMARY KEY REFERENCES runs(run_id),
    tp            INTEGER NOT NULL,
    fp            INTEGER NOT NULL,
    fn            INTEGER NOT NULL,
    recall        REAL NOT NULL,
    precision     REAL NOT NULL,
    f1            REAL NOT NULL,
    order_penalty REAL
);
```

## 3. Index strategy

```sql
CREATE INDEX IF NOT EXISTS idx_events_scenario ON events(scenario_id);
CREATE INDEX IF NOT EXISTS idx_events_time     ON events(event_time);
CREATE INDEX IF NOT EXISTS idx_events_source   ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_prefilter ON events(pre_filter_passed);
CREATE INDEX IF NOT EXISTS idx_runs_scenario   ON runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_runs_arm        ON runs(arm);
```

Rationale: queries are dominated by "all events for a scenario" (collectors, arms), "events in a time window"
(temporal correlation / clock model), and "all runs of an arm/scenario" (analysis). The `(arm, scenario_id,
seed)` uniqueness constraint enforces the repeated-measures design from `01` §4.

## 4. Retention / TTL

- **Benchmark data is reproducible by construction** (re-run the simulator), so the cache can be rebuilt. No
  aggressive TTL is required during development.
- **Policy:** `events` and `agent_outputs` for a given `scenario_id` are **truncated and regenerated** on each
  fresh simulator run of that scenario (idempotent by `scenario_id`). `runs`/`scores` are **append-only**
  within an experiment, keyed by `run_id`, so multi-seed history is preserved for variance reporting.
- **Held-out isolation:** rows with `scenarios.is_held_out = 1` must not be populated with `runs`/`scores`
  until P4 (enforced by the runner, not the schema). See `02` §3.6.

## 5. Notes

- `event_id` values are the same strings used in manifest `evidence_event_ids` (`03`) — this is what lets the
  matching function's evidence-binding check (`04` §2.2) work.
- `model_version` is stored per run but must be **identical across A1–A4** within an experiment (held-fixed
  config, `01` §6).
