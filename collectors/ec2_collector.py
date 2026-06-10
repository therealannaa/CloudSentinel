import boto3
import json
import os
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
DB_PATH = os.getenv("DB_PATH", "cloudsentinel.db")

DANGEROUS_PORTS = [22, 3389, 1433, 3306, 5432]
APPROVED_REGIONS = os.getenv("APPROVED_REGIONS", "ap-south-1").split(",")

def get_ec2_client(region="ap-south-1"):
    return boto3.client(
        "ec2",
        endpoint_url=LOCALSTACK_URL,
        region_name=region,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ec2_instances (
            instance_id TEXT PRIMARY KEY,
            instance_type TEXT,
            region TEXT,
            launch_time TEXT,
            state TEXT,
            imdsv2_enabled INTEGER,
            security_groups TEXT,
            first_seen TEXT,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[EC2] Database initialized at {DB_PATH}")

def save_instance(instance):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()

    cursor.execute('''
        INSERT OR REPLACE INTO ec2_instances
        (instance_id, instance_type, region, launch_time, state,
         imdsv2_enabled, security_groups, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?, 
            COALESCE((SELECT first_seen FROM ec2_instances 
                      WHERE instance_id = ?), ?), ?)
    ''', (
        instance["instance_id"],
        instance["instance_type"],
        instance["region"],
        instance["launch_time"],
        instance["state"],
        instance["imdsv2_enabled"],
        json.dumps(instance["security_groups"]),
        instance["instance_id"],
        now,
        now
    ))
    conn.commit()
    conn.close()

def normalize_finding(event_type, severity, details, instance_id="unknown"):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "source_ip": instance_id,
        "event_type": event_type,
        "severity": severity,
        "raw_event": json.dumps(details),
        "agent_id": "compute_hunter",
        "username": "unknown",
    }

def check_security_groups(client, instance_id, sg_ids):
    findings = []
    for sg_id in sg_ids:
        try:
            response = client.describe_security_groups(GroupIds=[sg_id])
            for sg in response.get("SecurityGroups", []):
                for rule in sg.get("IpPermissions", []):
                    from_port = rule.get("FromPort", 0)
                    to_port = rule.get("ToPort", 65535)
                    for ip_range in rule.get("IpRanges", []):
                        cidr = ip_range.get("CidrIp", "")
                        if cidr == "0.0.0.0/0":
                            for port in DANGEROUS_PORTS:
                                if from_port <= port <= to_port:
                                    findings.append(normalize_finding(
                                        event_type="DANGEROUS_PORT_OPEN",
                                        severity="CRITICAL",
                                        details={
                                            "instance_id": instance_id,
                                            "security_group": sg_id,
                                            "port": port,
                                            "cidr": cidr,
                                            "mitre_technique": "T1190",
                                            "pci_dss": "Req 1.2"
                                        },
                                        instance_id=instance_id
                                    ))
                                    print(f"[EC2] CRITICAL — Port {port} open to 0.0.0.0/0 on {instance_id}")
        except Exception as e:
            print(f"[EC2] Could not check security group {sg_id}: {e}")

    return findings

def check_imdsv2(instance):
    findings = []
    metadata_options = instance.get("MetadataOptions", {})
    http_tokens = metadata_options.get("HttpTokens", "optional")

    if http_tokens != "required":
        findings.append(normalize_finding(
            event_type="IMDSV2_NOT_ENFORCED",
            severity="HIGH",
            details={
                "instance_id": instance.get("InstanceId"),
                "http_tokens": http_tokens,
                "mitre_technique": "T1552.005",
                "pci_dss": "Req 2.1",
                "description": "IMDSv2 not enforced — vulnerable to SSRF credential theft"
            },
            instance_id=instance.get("InstanceId", "unknown")
        ))
        print(f"[EC2] HIGH — IMDSv2 not enforced on {instance.get('InstanceId')}")

    return findings

def check_region(instance_id, region):
    findings = []
    if region not in APPROVED_REGIONS:
        findings.append(normalize_finding(
            event_type="INSTANCE_IN_UNAPPROVED_REGION",
            severity="HIGH",
            details={
                "instance_id": instance_id,
                "region": region,
                "approved_regions": APPROVED_REGIONS,
                "mitre_technique": "T1578",
                "pci_dss": "Req 12.1"
            },
            instance_id=instance_id
        ))
        print(f"[EC2] HIGH — Instance {instance_id} in unapproved region: {region}")

    return findings

def collect_ec2_events():
    init_db()
    client = get_ec2_client()
    findings = []

    try:
        response = client.describe_instances()
        reservations = response.get("Reservations", [])

        if not reservations:
            print("[EC2] No instances found — LocalStack may not be running or no instances exist")
            return findings

        print(f"[EC2] Found {len(reservations)} reservations")

        for reservation in reservations:
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId", "unknown")
                instance_type = instance.get("InstanceType", "unknown")
                region = "ap-south-1"
                launch_time = str(instance.get("LaunchTime", ""))
                state = instance.get("State", {}).get("Name", "unknown")
                sg_ids = [sg["GroupId"] for sg in instance.get("SecurityGroups", [])]
                imdsv2 = instance.get("MetadataOptions", {}).get("HttpTokens") == "required"

                instance_data = {
                    "instance_id": instance_id,
                    "instance_type": instance_type,
                    "region": region,
                    "launch_time": launch_time,
                    "state": state,
                    "imdsv2_enabled": int(imdsv2),
                    "security_groups": sg_ids,
                }
                save_instance(instance_data)

                findings += check_imdsv2(instance)
                findings += check_security_groups(client, instance_id, sg_ids)
                findings += check_region(instance_id, region)

    except Exception as e:
        print(f"[EC2] Error describing instances: {e}")

    print(f"[EC2] Total findings: {len(findings)}")
    return findings

if __name__ == "__main__":
    results = collect_ec2_events()
    print(json.dumps(results, indent=2, default=str))