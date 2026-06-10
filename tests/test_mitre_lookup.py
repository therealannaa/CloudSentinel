import pytest
from tools.mitre_lookup import (
    init_mitre_db, lookup_technique, lookup_techniques_by_platform,
    get_all_techniques, get_mitigation, enrich_finding, CLOUD_TECHNIQUES,
)


@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "test_mitre.db")
    init_mitre_db(db_path)
    return db_path


class TestMITRELookup:
    def test_lookup_t1078(self, db):
        result = lookup_technique("T1078", db)
        assert result is not None
        assert result["name"] == "Valid Accounts"
        assert "MFA" in result["mitigation"]

    def test_lookup_t1530(self, db):
        result = lookup_technique("T1530", db)
        assert result is not None
        assert result["name"] == "Data from Cloud Storage Object"

    def test_lookup_t1496(self, db):
        result = lookup_technique("T1496", db)
        assert result is not None
        assert result["name"] == "Resource Hijacking"
        assert "crypto" in result["description"].lower() or "compute" in result["description"].lower()

    def test_lookup_nonexistent(self, db):
        assert lookup_technique("T9999", db) is None

    def test_lookup_subtechnique(self, db):
        result = lookup_technique("T1552.005", db)
        assert result is not None
        assert "IMDSv2" in result["mitigation"]


class TestAnnaCompatibility:
    def test_all_anna_techniques_present(self, db):
        anna_techniques = ["T1046", "T1190", "T1530", "T1537", "T1552.005", "T1578"]
        for tid in anna_techniques:
            result = lookup_technique(tid, db)
            assert result is not None, f"{tid} missing from curated set"

    def test_task_required_techniques(self, db):
        required = ["T1078", "T1530", "T1496", "T1485", "T1098", "T1548"]
        for tid in required:
            assert lookup_technique(tid, db) is not None, f"{tid} missing"


class TestPlatformFilter:
    def test_aws_filter(self, db):
        results = lookup_techniques_by_platform("AWS", db)
        assert len(results) > 0
        for r in results:
            assert "AWS" in r["platforms"]

    def test_all_techniques_have_aws(self, db):
        all_techs = get_all_techniques(db)
        for t in all_techs:
            assert "AWS" in t["platforms"]


class TestConvenience:
    def test_get_mitigation(self, db):
        mit = get_mitigation("T1078", db)
        assert mit is not None
        assert isinstance(mit, str)
        assert len(mit) > 10

    def test_get_mitigation_nonexistent(self, db):
        assert get_mitigation("T9999", db) is None

    def test_curated_dict_matches_db(self, db):
        all_db = get_all_techniques(db)
        db_ids = {t["technique_id"] for t in all_db}
        for tid in CLOUD_TECHNIQUES:
            assert tid in db_ids

    def test_get_all_count(self, db):
        all_techs = get_all_techniques(db)
        assert len(all_techs) == len(CLOUD_TECHNIQUES)


class TestEnrichFinding:
    def test_enrich_with_known_technique(self, db):
        finding = {
            "timestamp": "2026-06-09T10:00:00",
            "source_ip": "10.0.0.1",
            "event_type": "DANGEROUS_PORT_OPEN",
            "severity": "CRITICAL",
            "raw_event": '{"mitre_technique": "T1190", "port": 22}',
            "agent_id": "compute_hunter",
            "username": "unknown",
        }
        enriched = enrich_finding(finding, db)
        assert enriched["mitre_name"] == "Exploit Public-Facing Application"
        assert "mitre_mitigation" in enriched
        assert enriched["event_type"] == "DANGEROUS_PORT_OPEN"

    def test_enrich_without_technique(self, db):
        finding = {
            "timestamp": "2026-06-09T10:00:00",
            "event_type": "UNKNOWN",
            "severity": "LOW",
            "raw_event": "{}",
            "agent_id": "test",
            "username": "unknown",
        }
        enriched = enrich_finding(finding, db)
        assert "mitre_name" not in enriched

    def test_enrich_preserves_original(self, db):
        finding = {"timestamp": "t", "event_type": "E", "raw_event": "{}",
                    "severity": "LOW", "agent_id": "x", "username": "u"}
        enriched = enrich_finding(finding, db)
        assert finding == {"timestamp": "t", "event_type": "E", "raw_event": "{}",
                           "severity": "LOW", "agent_id": "x", "username": "u"}
