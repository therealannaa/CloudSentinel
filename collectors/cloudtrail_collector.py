import boto3
import json
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os

load_dotenv()

LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")

SUSPICIOUS_EVENTS = [
    "ConsoleLogin",
    "CreateUser",
    "AttachUserPolicy",
    "PutUserPolicy",
    "CreateAccessKey",
    "AssumeRole",
    "DeleteTrail",
    "StopLogging",
    "PutBucketPolicy",
]

def get_cloudtrail_client():
    return boto3.client(
        "cloudtrail",
        endpoint_url=LOCALSTACK_URL,
        region_name="ap-south-1",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )

def normalize_finding(event):
    return {
        "timestamp": str(event.get("EventTime", "")),
        "source_ip": event.get("CloudTrailEvent", "{}"),
        "event_type": event.get("EventName", ""),
        "severity": "HIGH" if event.get("EventName") in [
            "CreateUser", "AttachUserPolicy", "DeleteTrail"
        ] else "MEDIUM",
        "raw_event": event.get("CloudTrailEvent", "{}"),
        "agent_id": "identity_hunter",
        "username": event.get("Username", "unknown"),
    }

def collect_suspicious_events(hours=24):
    client = get_cloudtrail_client()
    findings = []

    start_time = datetime.now(timezone.utc) - timedelta(hours=hours)

    for event_name in SUSPICIOUS_EVENTS:
        try:
            response = client.lookup_events(
                LookupAttributes=[{
                    "AttributeKey": "EventName",
                    "AttributeValue": event_name
                }],
                StartTime=start_time,
                MaxResults=50
            )

            for event in response.get("Events", []):
                finding = normalize_finding(event)
                findings.append(finding)
                print(f"[CloudTrail] Found: {event_name} by {finding['username']} at {finding['timestamp']}")

        except Exception as e:
            print(f"[CloudTrail] Error fetching {event_name}: {e}")

    print(f"[CloudTrail] Total suspicious events found: {len(findings)}")
    return findings

if __name__ == "__main__":
    results = collect_suspicious_events()
    print(json.dumps(results, indent=2, default=str))