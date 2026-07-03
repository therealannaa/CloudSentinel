import sqlite3
import json

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DB_PATH


CLOUD_TECHNIQUES = {
    "T1078": {
        "name": "Valid Accounts",
        "description": "Adversaries may obtain and abuse credentials of existing accounts as a means of gaining Initial Access, Persistence, Privilege Escalation, or Defense Evasion.",
        "mitigation": "Enable MFA for all accounts. Enforce credential rotation policies. Monitor for anomalous login patterns including unusual geolocations and impossible travel.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure AD Logs,GCP Audit Logs",
    },
    "T1078.004": {
        "name": "Valid Accounts: Cloud Accounts",
        "description": "Adversaries may obtain and abuse credentials of cloud accounts to gain access to cloud services and resources.",
        "mitigation": "Enforce MFA on all cloud accounts. Use conditional access policies. Monitor for unusual API activity from cloud credentials.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure AD Logs,GCP Audit Logs",
    },
    "T1046": {
        "name": "Network Service Discovery",
        "description": "Adversaries may attempt to get a listing of services running on remote hosts and local network infrastructure devices, including those that may be vulnerable to remote software exploitation.",
        "mitigation": "Use network segmentation. Deploy IDS/IPS to detect port scanning. Restrict unnecessary network services.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "VPC Flow Logs,Network Traffic,Zeek Logs",
    },
    "T1098": {
        "name": "Account Manipulation",
        "description": "Adversaries may manipulate accounts to maintain or elevate access to victim systems. This includes modifying credentials, permissions, or creating additional accounts.",
        "mitigation": "Monitor IAM policy changes. Alert on CreateUser and AttachUserPolicy events. Enforce least privilege access.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure AD Logs,GCP Admin Activity",
    },
    "T1098.001": {
        "name": "Account Manipulation: Additional Cloud Credentials",
        "description": "Adversaries may add adversary-controlled credentials (access keys or login profiles) to a cloud account to maintain persistent access. Creating an access key on another user's account is a common AWS variant.",
        "mitigation": "Alert on CreateAccessKey / CreateLoginProfile for principals that do not normally rotate keys. Enforce least privilege on iam:CreateAccessKey. Rotate and audit access keys.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure AD Logs,GCP Admin Activity",
    },
    "T1110": {
        "name": "Brute Force",
        "description": "Adversaries may use brute force techniques to gain access to accounts when passwords are unknown or when password hashes are obtained.",
        "mitigation": "Enforce account lockout policies. Implement MFA. Monitor for multiple failed authentication attempts.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure AD Sign-in Logs",
    },
    "T1190": {
        "name": "Exploit Public-Facing Application",
        "description": "Adversaries may attempt to exploit a weakness in an Internet-facing host or system to initially access a network. Security group misconfigurations exposing dangerous ports enable this.",
        "mitigation": "Restrict security group ingress rules. Close unnecessary ports (22, 3389, 1433). Use WAF for public-facing applications.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,VPC Flow Logs,Application Logs",
    },
    "T1485": {
        "name": "Data Destruction",
        "description": "Adversaries may destroy data and files on specific systems or in large numbers on a network to interrupt availability. Bulk S3 object deletion is a common cloud variant.",
        "mitigation": "Enable S3 versioning and MFA Delete. Implement Object Lock for critical buckets. Set up cross-region replication.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "S3 Access Logs,CloudTrail,CloudWatch",
    },
    "T1496": {
        "name": "Resource Hijacking",
        "description": "Adversaries may leverage the compute resources of co-opted systems to complete resource-intensive tasks such as cryptocurrency mining.",
        "mitigation": "Monitor CPU and GPU utilization anomalies. Set AWS billing alerts. Restrict instance types via Service Control Policies.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudWatch,CloudTrail,Process Monitoring",
    },
    "T1526": {
        "name": "Cloud Service Discovery",
        "description": "Adversaries may attempt to enumerate cloud services running on a system after gaining access. This can help identify targets for further exploitation.",
        "mitigation": "Restrict IAM permissions using least privilege. Monitor unusual API enumeration patterns in CloudTrail.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure Activity Logs",
    },
    "T1528": {
        "name": "Steal Application Access Token",
        "description": "Adversaries can steal application access tokens as a means of acquiring credentials to access remote systems and resources.",
        "mitigation": "Rotate access tokens regularly. Monitor for unusual token usage. Use short-lived credentials via STS.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,OAuth Logs",
    },
    "T1530": {
        "name": "Data from Cloud Storage Object",
        "description": "Adversaries may access data from improperly secured cloud storage. Mass downloads from S3 buckets or publicly accessible buckets indicate this technique.",
        "mitigation": "Enforce bucket policies denying public access. Enable S3 access logging. Use S3 Block Public Access at account level.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "S3 Access Logs,CloudTrail,S3 Server Access Logs",
    },
    "T1537": {
        "name": "Transfer Data to Cloud Account",
        "description": "Adversaries may exfiltrate data by transferring it to another cloud account they control. Large outbound transfers to external IPs are an indicator.",
        "mitigation": "Monitor VPC Flow Logs for large outbound transfers. Set up data transfer alerts. Use VPC endpoints to restrict S3 access.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "VPC Flow Logs,CloudTrail,Network Traffic",
    },
    "T1548": {
        "name": "Abuse Elevation Control Mechanism",
        "description": "Adversaries may circumvent mechanisms designed to control elevated privileges to gain higher-level permissions.",
        "mitigation": "Enforce least privilege IAM policies. Monitor AssumeRole calls. Restrict who can modify IAM policies.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,IAM Access Analyzer",
    },
    "T1548.005": {
        "name": "Abuse Elevation Control Mechanism: Temporary Elevated Cloud Access",
        "description": "Adversaries may abuse permissions that let them assume roles or request temporary elevated access (e.g. sts:AssumeRole) to gain higher privileges than their base principal holds. Role chaining extends this across accounts.",
        "mitigation": "Restrict which principals may assume sensitive roles. Monitor AssumeRole calls and role-chaining. Apply permission boundaries and session policies.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,IAM Access Analyzer",
    },
    "T1552.005": {
        "name": "Unsecured Credentials: Cloud Instance Metadata API",
        "description": "Adversaries may attempt to access the cloud instance metadata API to collect credentials. IMDSv1 on EC2 instances is vulnerable to SSRF-based credential theft.",
        "mitigation": "Enforce IMDSv2 on all EC2 instances. Set HttpTokens to 'required'. Monitor for metadata API access patterns.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Instance Metadata Logs",
    },
    "T1562.001": {
        "name": "Impair Defenses: Disable or Modify Tools",
        "description": "Adversaries may disable security tools to avoid detection. In cloud environments this includes stopping CloudTrail logging or deleting trails.",
        "mitigation": "Enable CloudTrail log file validation. Use SCPs to prevent StopLogging/DeleteTrail. Alert immediately on logging changes.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,CloudWatch Events",
    },
    "T1562.008": {
        "name": "Impair Defenses: Disable Cloud Logs",
        "description": "Adversaries may disable cloud logging to evade detection, e.g. StopLogging or DeleteTrail on AWS CloudTrail, removing the audit trail of their activity.",
        "mitigation": "Use SCPs to deny cloudtrail:StopLogging / DeleteTrail. Enable log-file validation and alert immediately on any logging state change. Deliver logs to a separate, locked-down account.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,CloudWatch Events",
    },
    "T1571": {
        "name": "Non-Standard Port",
        "description": "Adversaries may communicate using a protocol and port pairing that are typically not associated, to bypass filtering or muddle analysis.",
        "mitigation": "Monitor for non-standard port usage in VPC Flow Logs. Implement egress filtering. Use protocol-aware firewalls.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "VPC Flow Logs,Zeek Logs,Network Traffic",
    },
    "T1578": {
        "name": "Modify Cloud Compute Infrastructure",
        "description": "Adversaries may modify cloud compute infrastructure to evade defenses, including launching instances in unapproved regions or modifying instance attributes.",
        "mitigation": "Restrict instance launches to approved regions via SCPs. Monitor RunInstances events. Alert on region anomalies.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,AWS Config",
    },
    "T1580": {
        "name": "Cloud Infrastructure Discovery",
        "description": "Adversaries may attempt to discover cloud infrastructure components like EC2 instances, S3 buckets, and IAM roles after gaining initial access.",
        "mitigation": "Restrict DescribeInstances and ListBuckets permissions. Monitor for enumeration activity spikes.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "CloudTrail,Azure Activity Logs",
    },
    "T1595": {
        "name": "Active Scanning",
        "description": "Adversaries may execute active reconnaissance scans to gather information that can be used during targeting. Includes scanning for open ports and vulnerable services.",
        "mitigation": "Deploy network-based IDS. Monitor for scanning patterns in VPC Flow Logs. Use AWS Shield for DDoS scanning protection.",
        "platforms": "AWS,Azure,GCP",
        "data_sources": "VPC Flow Logs,Zeek Logs,Network IDS",
    },
}


def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_mitre_db(db_path=None):
    conn = get_connection(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mitre_techniques (
            technique_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            mitigation TEXT NOT NULL,
            platforms TEXT,
            data_sources TEXT
        )
    """)
    for tid, data in CLOUD_TECHNIQUES.items():
        conn.execute("""
            INSERT OR REPLACE INTO mitre_techniques
                (technique_id, name, description, mitigation, platforms, data_sources)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tid, data["name"], data["description"], data["mitigation"],
              data["platforms"], data["data_sources"]))
    conn.commit()
    conn.close()


def lookup_technique(technique_id, db_path=None):
    conn = get_connection(db_path)
    row = conn.execute(
        "SELECT * FROM mitre_techniques WHERE technique_id = ?", (technique_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def lookup_techniques_by_platform(platform, db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM mitre_techniques WHERE platforms LIKE ?", (f"%{platform}%",)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_techniques(db_path=None):
    conn = get_connection(db_path)
    rows = conn.execute("SELECT * FROM mitre_techniques").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_mitigation(technique_id, db_path=None):
    result = lookup_technique(technique_id, db_path)
    return result["mitigation"] if result else None


def enrich_finding(finding, db_path=None):
    """Takes a normalized Finding dict, looks up the MITRE technique from raw_event,
    and adds mitre_name and mitre_mitigation fields. Returns a new dict."""
    enriched = dict(finding)
    raw_event = finding.get("raw_event", "{}")

    technique_id = None
    try:
        raw = json.loads(raw_event) if isinstance(raw_event, str) else raw_event
        technique_id = raw.get("mitre_technique")
    except (json.JSONDecodeError, AttributeError):
        pass

    if technique_id:
        result = lookup_technique(technique_id, db_path)
        if result:
            enriched["mitre_name"] = result["name"]
            enriched["mitre_mitigation"] = result["mitigation"]
            enriched["mitre_description"] = result["description"]

    return enriched
