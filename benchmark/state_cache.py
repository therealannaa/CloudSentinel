"""SQLite shared state cache — implements docs/week1/05_sqlite_state_cache_schema.md.

All benchmark state (scenarios, captured events, runs, reconstructed chains,
agent outputs, scores) lives in one sqlite file (DB_PATH from config.py). The
v1 tables (ec2_instances, baseline tables, mitre_techniques) live in the same
file and are untouched here.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

DDL = """
CREATE TABLE IF NOT EXISTS scenarios (
    scenario_id   TEXT PRIMARY KEY,
    category      TEXT NOT NULL,
    is_held_out   INTEGER NOT NULL DEFAULT 0,
    manifest_path TEXT,
    author        TEXT,
    reviewer      TEXT,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
    event_id          TEXT PRIMARY KEY,
    scenario_id       TEXT NOT NULL REFERENCES scenarios(scenario_id),
    environment       TEXT NOT NULL DEFAULT 'synthetic',
    source            TEXT NOT NULL,
    event_time        TEXT NOT NULL,
    raw_json          TEXT NOT NULL,
    normalized_json   TEXT,
    pre_filter_passed INTEGER NOT NULL DEFAULT 0,
    is_ground_truth   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS runs (
    run_id               TEXT PRIMARY KEY,
    arm                  TEXT NOT NULL,
    environment          TEXT NOT NULL,
    scenario_id          TEXT NOT NULL REFERENCES scenarios(scenario_id),
    seed                 INTEGER NOT NULL,
    model_version        TEXT,
    started_at           TEXT NOT NULL,
    finished_at          TEXT,
    latency_ms           INTEGER,
    token_cost           INTEGER,
    prefilter_events_in  INTEGER,
    prefilter_events_out INTEGER,
    UNIQUE (arm, scenario_id, seed, environment)
);

CREATE TABLE IF NOT EXISTS reconstructed_stages (
    run_id             TEXT NOT NULL REFERENCES runs(run_id),
    stage_id           INTEGER NOT NULL,
    ttp_id             TEXT NOT NULL,
    telemetry_source   TEXT NOT NULL,
    evidence_event_ids TEXT NOT NULL,
    t_start            TEXT,
    t_end              TEXT,
    PRIMARY KEY (run_id, stage_id)
);

CREATE TABLE IF NOT EXISTS agent_outputs (
    run_id      TEXT NOT NULL REFERENCES runs(run_id),
    agent_id    TEXT NOT NULL,
    output_json TEXT NOT NULL,
    PRIMARY KEY (run_id, agent_id)
);

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

CREATE INDEX IF NOT EXISTS idx_events_scenario  ON events(scenario_id);
CREATE INDEX IF NOT EXISTS idx_events_time      ON events(event_time);
CREATE INDEX IF NOT EXISTS idx_events_source    ON events(source);
CREATE INDEX IF NOT EXISTS idx_events_prefilter ON events(pre_filter_passed);
CREATE INDEX IF NOT EXISTS idx_runs_scenario    ON runs(scenario_id);
CREATE INDEX IF NOT EXISTS idx_runs_arm         ON runs(arm);
"""


def _now():
    return datetime.now(timezone.utc).isoformat()


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_state_cache(db_path):
    """Create all benchmark tables + indexes (idempotent)."""
    conn = connect(db_path)
    conn.executescript(DDL)
    conn.commit()
    return conn


def upsert_scenario(conn, scenario_id, category, is_held_out=False,
                    manifest_path=None, author=None, reviewer=None):
    conn.execute(
        """INSERT INTO scenarios
               (scenario_id, category, is_held_out, manifest_path, author, reviewer, created_at)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(scenario_id) DO UPDATE SET
               category=excluded.category, is_held_out=excluded.is_held_out,
               manifest_path=excluded.manifest_path, author=excluded.author,
               reviewer=excluded.reviewer""",
        (scenario_id, category, int(is_held_out), manifest_path, author, reviewer, _now()),
    )
    conn.commit()


def insert_events(conn, events):
    """Bulk-insert Event objects. Re-running a scenario replaces its events
    (idempotent by scenario_id, per the docs/week1/05 retention policy)."""
    if not events:
        return 0
    scenario_ids = {e.scenario_id for e in events}
    for sid in scenario_ids:
        conn.execute("DELETE FROM events WHERE scenario_id = ?", (sid,))
    conn.executemany(
        """INSERT INTO events
               (event_id, scenario_id, environment, source, event_time,
                raw_json, normalized_json, pre_filter_passed, is_ground_truth)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        [e.to_row() for e in events],
    )
    conn.commit()
    return len(events)


def event_count(conn, scenario_id=None):
    if scenario_id:
        cur = conn.execute("SELECT COUNT(*) FROM events WHERE scenario_id=?", (scenario_id,))
    else:
        cur = conn.execute("SELECT COUNT(*) FROM events")
    return cur.fetchone()[0]


def insert_run(conn, run_id, arm, environment, scenario_id, seed,
               model_version=None, latency_ms=None, token_cost=None,
               prefilter_events_in=None, prefilter_events_out=None):
    conn.execute(
        """INSERT OR REPLACE INTO runs
               (run_id, arm, environment, scenario_id, seed, model_version,
                started_at, finished_at, latency_ms, token_cost,
                prefilter_events_in, prefilter_events_out)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (run_id, arm, environment, scenario_id, seed, model_version,
         _now(), _now(), latency_ms, token_cost,
         prefilter_events_in, prefilter_events_out),
    )
    conn.commit()


def insert_score(conn, run_id, score_result):
    s = score_result
    conn.execute(
        """INSERT OR REPLACE INTO scores
               (run_id, tp, fp, fn, recall, precision, f1, order_penalty)
           VALUES (?,?,?,?,?,?,?,?)""",
        (run_id, s.tp, s.fp, s.fn, s.recall, s.precision, s.f1, s.order_penalty),
    )
    conn.commit()


def scenario_summary(conn):
    """Per-category scenario + event counts (sanity / DoD check)."""
    rows = conn.execute(
        """SELECT s.category,
                  COUNT(DISTINCT s.scenario_id) AS n_scenarios,
                  COUNT(e.event_id) AS n_events,
                  SUM(e.is_ground_truth) AS n_ground_truth
           FROM scenarios s LEFT JOIN events e ON e.scenario_id = s.scenario_id
           GROUP BY s.category ORDER BY s.category"""
    ).fetchall()
    return [dict(r) for r in rows]
