# CloudSentinel Data Schemas

## Normalized Finding (JSON)

Every collector and agent produces findings in this format.

| Field       | Type   | Description                                   | Example                        |
|-------------|--------|-----------------------------------------------|--------------------------------|
| timestamp   | string | ISO 8601 UTC timestamp                        | `"2026-06-09T10:00:00"`        |
| source_ip   | string | Source IP address or instance ID               | `"203.0.113.5"` or `"i-abc123"` |
| event_type  | string | Detection event type (UPPER_SNAKE_CASE)        | `"DANGEROUS_PORT_OPEN"`        |
| severity    | string | CRITICAL, HIGH, MEDIUM, or LOW                 | `"CRITICAL"`                   |
| raw_event   | string | JSON string with event-specific details         | `'{"port": 22, "mitre_technique": "T1190"}'` |
| agent_id    | string | Agent that produced the finding                 | `"compute_hunter"`             |
| username    | string | Associated IAM user or `"unknown"`              | `"admin"`                      |

**Note:** The `source_ip` field may contain an instance ID instead of an IP address in some collectors (e.g., ec2_collector uses instance_id). The cloudtrail_collector currently sets this to the full CloudTrail event JSON — this is a known inconsistency to be fixed.

## Agent IDs

- `identity_hunter` — CloudTrail/IAM findings
- `network_hunter` — VPC Flow/Zeek findings
- `data_hunter` — S3 findings
- `compute_hunter` — EC2 findings
- `threat_intel_enricher` — Enrichment findings (Week 3)
- `coordinator` — Cross-domain correlation (Week 3)

## Event Types

| Event Type                    | Agent           | MITRE Technique |
|-------------------------------|-----------------|-----------------|
| `DANGEROUS_PORT_OPEN`         | compute_hunter  | T1190           |
| `IMDSV2_NOT_ENFORCED`         | compute_hunter  | T1552.005       |
| `INSTANCE_IN_UNAPPROVED_REGION` | compute_hunter | T1578          |
| `PORT_SCAN_DETECTED`          | network_hunter  | T1046           |
| `LARGE_OUTBOUND_TRANSFER`     | network_hunter  | T1537           |
| `PUBLIC_BUCKET_ACL_DETECTED`  | data_hunter     | T1530           |
| `BUCKET_ENCRYPTION_DISABLED`  | data_hunter     | T1530           |
| `MASS_DOWNLOAD_RISK`          | data_hunter     | T1530           |

## SQLite Tables

### Collector tables

| Table           | Owner              | Purpose                    |
|-----------------|--------------------|----------------------------|
| `ec2_instances` | ec2_collector.py   | Raw EC2 instance state     |

### Baseline & tools tables

| Table                | Owner           | Purpose                        |
|----------------------|-----------------|--------------------------------|
| `instances_baseline` | baseline.py     | Behavioral baseline per instance |
| `ip_history`         | baseline.py     | IP-to-instance association history |
| `access_patterns`    | baseline.py     | User access pattern baseline    |
| `alerts`             | baseline.py     | Generated alerts with dedup     |
| `mitre_techniques`   | mitre_lookup.py | Curated ATT&CK technique data  |

All tables live in the same `cloudsentinel.db` file (configurable via `DB_PATH` env var).
