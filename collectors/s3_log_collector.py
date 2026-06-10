import boto3
import json
import os
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
MASS_DOWNLOAD_THRESHOLD = int(os.getenv("MASS_DOWNLOAD_THRESHOLD", "50"))
BULK_DELETE_THRESHOLD = int(os.getenv("BULK_DELETE_THRESHOLD", "20"))
MASS_DOWNLOAD_WINDOW = int(os.getenv("MASS_DOWNLOAD_WINDOW", "300"))

DANGEROUS_ACL = ["public-read", "public-read-write", "authenticated-read"]

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_URL,
        region_name="ap-south-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )

def normalize_finding(event_type, severity, details, source_ip="unknown", username="unknown"):
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "source_ip": source_ip,
        "event_type": event_type,
        "severity": severity,
        "raw_event": json.dumps(details),
        "agent_id": "data_hunter",
        "username": username,
    }

def get_all_buckets(client):
    try:
        response = client.list_buckets()
        return [b["Name"] for b in response.get("Buckets", [])]
    except Exception as e:
        print(f"[S3] Error listing buckets: {e}")
        return []

def check_bucket_acl(client, bucket_name):
    findings = []
    try:
        acl = client.get_bucket_acl(Bucket=bucket_name)
        for grant in acl.get("Grants", []):
            grantee = grant.get("Grantee", {})
            permission = grant.get("Permission", "")
            uri = grantee.get("URI", "")

            if "AllUsers" in uri or "AuthenticatedUsers" in uri:
                findings.append(normalize_finding(
                    event_type="PUBLIC_BUCKET_ACL_DETECTED",
                    severity="CRITICAL",
                    details={
                        "bucket": bucket_name,
                        "permission": permission,
                        "grantee_uri": uri,
                        "mitre_technique": "T1530",
                        "pci_dss": "Req 3.1"
                    }
                ))
                print(f"[S3] CRITICAL — Public ACL on bucket: {bucket_name} ({permission})")

    except Exception as e:
        print(f"[S3] Could not check ACL for {bucket_name}: {e}")

    return findings

def check_bucket_encryption(client, bucket_name):
    findings = []
    try:
        client.get_bucket_encryption(Bucket=bucket_name)
    except client.exceptions.ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ServerSideEncryptionConfigurationNotFoundError":
            findings.append(normalize_finding(
                event_type="BUCKET_ENCRYPTION_DISABLED",
                severity="HIGH",
                details={
                    "bucket": bucket_name,
                    "mitre_technique": "T1530",
                    "pci_dss": "Req 4.1"
                }
            ))
            print(f"[S3] HIGH — Encryption disabled on bucket: {bucket_name}")
    except Exception as e:
        print(f"[S3] Could not check encryption for {bucket_name}: {e}")

    return findings

def check_mass_downloads(client, bucket_name):
    findings = []
    try:
        response = client.list_objects_v2(Bucket=bucket_name)
        object_count = response.get("KeyCount", 0)

        if object_count >= MASS_DOWNLOAD_THRESHOLD:
            findings.append(normalize_finding(
                event_type="MASS_DOWNLOAD_RISK",
                severity="HIGH",
                details={
                    "bucket": bucket_name,
                    "object_count": object_count,
                    "threshold": MASS_DOWNLOAD_THRESHOLD,
                    "mitre_technique": "T1530",
                    "pci_dss": "Req 3.1"
                }
            ))
            print(f"[S3] HIGH — Mass download risk on {bucket_name}: {object_count} objects")

    except Exception as e:
        print(f"[S3] Could not check objects for {bucket_name}: {e}")

    return findings

def collect_s3_events():
    client = get_s3_client()
    findings = []

    buckets = get_all_buckets(client)
    if not buckets:
        print("[S3] No buckets found — LocalStack may not be running")
        return findings

    print(f"[S3] Scanning {len(buckets)} buckets...")

    for bucket in buckets:
        findings += check_bucket_acl(client, bucket)
        findings += check_bucket_encryption(client, bucket)
        findings += check_mass_downloads(client, bucket)

    print(f"[S3] Total findings: {len(findings)}")
    return findings

if __name__ == "__main__":
    results = collect_s3_events()
    print(json.dumps(results, indent=2, default=str))