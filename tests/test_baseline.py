import pytest
from tools.baseline import (
    init_baseline_db, record_instance, get_baseline, update_baseline,
    record_instance_termination, get_ephemeral_instances,
    record_ip, get_ip_history,
    record_access_pattern, get_access_patterns,
    record_alert, get_open_alerts, resolve_alert,
    ingest_finding,
)


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_baseline_db(db_path)
    return db_path


class TestInstanceBaseline:
    def test_record_and_get(self, db):
        record_instance("i-abc123", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        baseline = get_baseline("i-abc123", db)
        assert baseline is not None
        assert baseline["instance_type"] == "t3.micro"
        assert baseline["region"] == "ap-south-1"

    def test_get_nonexistent(self, db):
        assert get_baseline("i-nonexistent", db) is None

    def test_update_metrics(self, db):
        record_instance("i-abc123", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        result = update_baseline("i-abc123", db, baseline_cpu_avg=45.2, risk_score=60)
        assert result is True
        baseline = get_baseline("i-abc123", db)
        assert baseline["baseline_cpu_avg"] == 45.2
        assert baseline["risk_score"] == 60

    def test_update_nonexistent_returns_false(self, db):
        assert update_baseline("i-nonexistent", db, risk_score=50) is False

    def test_record_preserves_first_seen(self, db):
        record_instance("i-abc123", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        first = get_baseline("i-abc123", db)["first_seen"]
        record_instance("i-abc123", "t3.large", "ap-south-1", "2026-06-09T10:00:00", db)
        assert get_baseline("i-abc123", db)["first_seen"] == first
        assert get_baseline("i-abc123", db)["instance_type"] == "t3.large"


class TestEphemeralDetection:
    def test_short_lived_flagged(self, db):
        record_instance("i-short", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        result = record_instance_termination("i-short", "2026-06-09T10:05:00", db)
        assert result["is_ephemeral"] is True
        assert result["lifetime_seconds"] == 300

    def test_long_lived_not_flagged(self, db):
        record_instance("i-long", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        result = record_instance_termination("i-long", "2026-06-09T11:00:00", db)
        assert result["is_ephemeral"] is False

    def test_get_ephemeral_instances(self, db):
        record_instance("i-eph1", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        record_instance_termination("i-eph1", "2026-06-09T10:05:00", db)
        record_instance("i-normal", "t3.micro", "ap-south-1", "2026-06-09T10:00:00", db)
        ephemerals = get_ephemeral_instances(db)
        assert len(ephemerals) == 1
        assert ephemerals[0]["instance_id"] == "i-eph1"

    def test_termination_nonexistent_returns_none(self, db):
        assert record_instance_termination("i-nope", "2026-06-09T10:05:00", db) is None


class TestIPHistory:
    def test_record_and_retrieve(self, db):
        record_ip("i-abc123", "203.0.113.5", "public", db)
        history = get_ip_history("i-abc123", db)
        assert len(history) == 1
        assert history[0]["ip_address"] == "203.0.113.5"

    def test_duplicate_updates_last_seen(self, db):
        record_ip("i-abc123", "203.0.113.5", "public", db)
        first_seen = get_ip_history("i-abc123", db)[0]["first_seen"]
        record_ip("i-abc123", "203.0.113.5", "public", db)
        history = get_ip_history("i-abc123", db)
        assert len(history) == 1
        assert history[0]["first_seen"] == first_seen


class TestAccessPatterns:
    def test_record_increments_count(self, db):
        record_access_pattern("admin", "10.0.0.1", "ConsoleLogin", db)
        record_access_pattern("admin", "10.0.0.1", "ConsoleLogin", db)
        patterns = get_access_patterns("admin", db)
        assert len(patterns) == 1
        assert patterns[0]["occurrence_count"] == 2

    def test_different_events_separate(self, db):
        record_access_pattern("admin", "10.0.0.1", "ConsoleLogin", db)
        record_access_pattern("admin", "10.0.0.1", "CreateUser", db)
        patterns = get_access_patterns("admin", db)
        assert len(patterns) == 2


class TestAlerts:
    def test_create_and_retrieve(self, db):
        alert_id = record_alert("PORT_SCAN", "HIGH", "Port scan from 10.0.0.1", db_path=db)
        assert alert_id is not None
        alerts = get_open_alerts(db_path=db)
        assert len(alerts) == 1
        assert alerts[0]["alert_type"] == "PORT_SCAN"

    def test_resolve_alert(self, db):
        alert_id = record_alert("PORT_SCAN", "HIGH", "Port scan", db_path=db)
        assert resolve_alert(alert_id, db) is True
        assert len(get_open_alerts(db_path=db)) == 0

    def test_resolve_nonexistent(self, db):
        assert resolve_alert(9999, db) is False

    def test_filter_by_severity(self, db):
        record_alert("A", "HIGH", "desc", db_path=db)
        record_alert("B", "CRITICAL", "desc", db_path=db)
        assert len(get_open_alerts(severity="CRITICAL", db_path=db)) == 1


class TestIngestFinding:
    def test_ingest_anna_format(self, db):
        finding = {
            "timestamp": "2026-06-09T10:00:00",
            "source_ip": "203.0.113.5",
            "event_type": "DANGEROUS_PORT_OPEN",
            "severity": "CRITICAL",
            "raw_event": '{"mitre_technique": "T1190", "port": 22}',
            "agent_id": "compute_hunter",
            "username": "unknown",
        }
        alert_id = ingest_finding(finding, db)
        assert alert_id is not None
        alerts = get_open_alerts(db_path=db)
        assert len(alerts) == 1
        assert alerts[0]["mitre_technique"] == "T1190"

    def test_ingest_missing_timestamp_returns_none(self, db):
        finding = {"event_type": "TEST", "severity": "LOW"}
        assert ingest_finding(finding, db) is None

    def test_ingest_records_access_pattern(self, db):
        finding = {
            "timestamp": "2026-06-09T10:00:00",
            "source_ip": "10.0.0.1",
            "event_type": "ConsoleLogin",
            "severity": "MEDIUM",
            "raw_event": "{}",
            "agent_id": "identity_hunter",
            "username": "admin",
        }
        ingest_finding(finding, db)
        patterns = get_access_patterns("admin", db)
        assert len(patterns) == 1
        assert patterns[0]["event_type"] == "ConsoleLogin"
