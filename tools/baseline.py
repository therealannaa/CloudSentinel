import sqlite3
import json
from datetime import datetime, timezone

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DB_PATH, EPHEMERAL_INSTANCE_THRESHOLD


def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_baseline_db(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS instances_baseline (
            instance_id TEXT PRIMARY KEY,
            instance_type TEXT,
            region TEXT,
            launch_time TEXT,
            termination_time TEXT,
            is_ephemeral INTEGER DEFAULT 0,
            baseline_cpu_avg REAL,
            baseline_network_avg REAL,
            risk_score INTEGER DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_updated TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            ip_type TEXT NOT NULL DEFAULT 'public',
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(instance_id, ip_address)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            source_ip TEXT NOT NULL,
            event_type TEXT NOT NULL,
            hour_of_day INTEGER,
            day_of_week INTEGER,
            occurrence_count INTEGER DEFAULT 1,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            UNIQUE(username, source_ip, event_type)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            instance_id TEXT,
            source_ip TEXT,
            username TEXT,
            description TEXT NOT NULL,
            mitre_technique TEXT,
            raw_finding TEXT,
            risk_score INTEGER DEFAULT 0,
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL,
            resolved_at TEXT
        )
    """)

    conn.commit()
    conn.close()


# --- Instance Baseline ---

def record_instance(instance_id, instance_type, region, launch_time, db_path=None):
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO instances_baseline
            (instance_id, instance_type, region, launch_time, first_seen, last_updated)
        VALUES (?, ?, ?, ?, COALESCE(
            (SELECT first_seen FROM instances_baseline WHERE instance_id = ?), ?
        ), ?)
        ON CONFLICT(instance_id) DO UPDATE SET
            instance_type = excluded.instance_type,
            region = excluded.region,
            launch_time = excluded.launch_time,
            last_updated = excluded.last_updated
    """, (instance_id, instance_type, region, launch_time, instance_id, now, now))
    conn.commit()
    conn.close()


def get_baseline(instance_id, db_path=None):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM instances_baseline WHERE instance_id = ?", (instance_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_baseline(instance_id, db_path=None, baseline_cpu_avg=None,
                    baseline_network_avg=None, risk_score=None):
    conn = get_connection(db_path)
    existing = conn.execute(
        "SELECT instance_id FROM instances_baseline WHERE instance_id = ?",
        (instance_id,)
    ).fetchone()
    if not existing:
        conn.close()
        return False

    updates = []
    params = []
    if baseline_cpu_avg is not None:
        updates.append("baseline_cpu_avg = ?")
        params.append(baseline_cpu_avg)
    if baseline_network_avg is not None:
        updates.append("baseline_network_avg = ?")
        params.append(baseline_network_avg)
    if risk_score is not None:
        updates.append("risk_score = ?")
        params.append(risk_score)

    if updates:
        updates.append("last_updated = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(instance_id)
        conn.execute(
            f"UPDATE instances_baseline SET {', '.join(updates)} WHERE instance_id = ?",
            params
        )
        conn.commit()

    conn.close()
    return True


def record_instance_termination(instance_id, termination_time, db_path=None):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT launch_time FROM instances_baseline WHERE instance_id = ?",
        (instance_id,)
    ).fetchone()

    if not row:
        conn.close()
        return None

    launch = datetime.fromisoformat(row["launch_time"])
    termination = datetime.fromisoformat(termination_time)
    lifetime_seconds = int((termination - launch).total_seconds())
    is_ephemeral = lifetime_seconds < EPHEMERAL_INSTANCE_THRESHOLD

    conn.execute("""
        UPDATE instances_baseline
        SET termination_time = ?, is_ephemeral = ?, last_updated = ?
        WHERE instance_id = ?
    """, (termination_time, int(is_ephemeral), datetime.now(timezone.utc).isoformat(), instance_id))
    conn.commit()
    conn.close()

    return {
        "instance_id": instance_id,
        "lifetime_seconds": lifetime_seconds,
        "is_ephemeral": is_ephemeral,
    }


def get_ephemeral_instances(db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM instances_baseline WHERE is_ephemeral = 1"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- IP History ---

def record_ip(instance_id, ip_address, ip_type="public", db_path=None):
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("""
        INSERT INTO ip_history (instance_id, ip_address, ip_type, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(instance_id, ip_address) DO UPDATE SET last_seen = excluded.last_seen
    """, (instance_id, ip_address, ip_type, now, now))
    conn.commit()
    conn.close()


def get_ip_history(instance_id, db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM ip_history WHERE instance_id = ?", (instance_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Access Patterns ---

def record_access_pattern(username, source_ip, event_type, db_path=None):
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO access_patterns
            (username, source_ip, event_type, hour_of_day, day_of_week, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(username, source_ip, event_type) DO UPDATE SET
            occurrence_count = occurrence_count + 1,
            last_seen = excluded.last_seen,
            hour_of_day = excluded.hour_of_day,
            day_of_week = excluded.day_of_week
    """, (username, source_ip, event_type, now.hour, now.weekday(), now.isoformat(), now.isoformat()))
    conn.commit()
    conn.close()


def get_access_patterns(username, db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM access_patterns WHERE username = ?", (username,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --- Alerts ---

def record_alert(alert_type, severity, description, instance_id=None,
                 source_ip=None, username=None, mitre_technique=None,
                 raw_finding=None, risk_score=0, db_path=None):
    conn = get_connection(db_path)
    now = datetime.now(timezone.utc).isoformat()
    raw_json = json.dumps(raw_finding) if raw_finding else None
    cursor = conn.execute("""
        INSERT INTO alerts
            (alert_type, severity, instance_id, source_ip, username,
             description, mitre_technique, raw_finding, risk_score, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
    """, (alert_type, severity, instance_id, source_ip, username,
          description, mitre_technique, raw_json, risk_score, now))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_open_alerts(severity=None, db_path=None):
    conn = get_connection(db_path)
    if severity:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE status = 'open' AND severity = ?", (severity,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE status = 'open'"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def resolve_alert(alert_id, db_path=None):
    conn = get_connection(db_path)
    cursor = conn.execute("""
        UPDATE alerts SET status = 'resolved', resolved_at = ?
        WHERE id = ? AND status = 'open'
    """, (datetime.now(timezone.utc).isoformat(), alert_id))
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return updated


# --- Bridge: Ingest Anna's normalized Finding dicts ---

def ingest_finding(finding, db_path=None):
    timestamp = finding.get("timestamp")
    source_ip = finding.get("source_ip", "unknown")
    event_type = finding.get("event_type", "unknown")
    severity = finding.get("severity", "MEDIUM")
    raw_event = finding.get("raw_event", "{}")
    agent_id = finding.get("agent_id", "unknown")
    username = finding.get("username", "unknown")

    if not timestamp or not event_type:
        return None

    record_access_pattern(username, source_ip, event_type, db_path)

    mitre_technique = None
    try:
        raw = json.loads(raw_event) if isinstance(raw_event, str) else raw_event
        mitre_technique = raw.get("mitre_technique")
    except (json.JSONDecodeError, AttributeError):
        pass

    alert_id = record_alert(
        alert_type=event_type,
        severity=severity,
        description=f"[{agent_id}] {event_type} from {source_ip} by {username}",
        source_ip=source_ip,
        username=username,
        mitre_technique=mitre_technique,
        raw_finding=finding,
        db_path=db_path,
    )
    return alert_id
