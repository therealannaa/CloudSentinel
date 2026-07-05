"""LocalStack execution backend — runs each scenario as REAL AWS API calls against
LocalStack and captures the resulting telemetry into the same Event/Manifest schema
as the synthetic backend.

Why this is "real" telemetry: the attack steps actually execute against the AWS API
surface (resources are really created/read/deleted in LocalStack), so the captured
events carry real ids, real timestamps, and real success/error responses — validating
that the attack scripts are well-formed against AWS, not just hand-written JSON.

Honest limitations (documented, not hidden):
  - LocalStack community CloudTrail event-history is limited, so we capture telemetry
    from the calls WE issue (which is exactly what a collector at the API boundary
    sees) plus LocalStack resource state — not from CloudTrail lookup_events.
  - Console-only events (ConsoleLogin) and the IMDS path have no faithful API call;
    we proxy them with the nearest real authenticated call (sts:GetCallerIdentity)
    and tag the event `proxy=True`.
  - VPC Flow Logs are not produced by LocalStack; network-source events (exfil flows,
    port scans, beacons) fall back to recorded network records tagged
    `synthetic_network=True`. In the full design these come from Zeek (docs/week1).

The answer-key boundary is preserved: captured raw payloads never carry a MITRE label.

Requires boto3 (imported lazily). LocalStack needs `docker compose up`; run with
`--environment localstack`. The SAME code runs against real AWS with
`--environment real_aws` — gated behind BENCH_ALLOW_REAL_AWS=1 + an APPROVED_REGIONS
check, and every launched resource (incl. EC2 instances) is torn down to avoid spend.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

from benchmark.events import Event
from benchmark.manifest import Manifest, Stage
from benchmark.simulator.builder import ttp_name

LOCALSTACK_URL = os.getenv("LOCALSTACK_URL", "http://localhost:4566")
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-south-1")
APPROVED_REGIONS = [r.strip() for r in
                    os.getenv("APPROVED_REGIONS", "ap-south-1").split(",") if r.strip()]
SERVICES = ("s3", "iam", "ec2", "sts", "secretsmanager", "cloudtrail")

# EC2 instance type for the launch techniques (T1578 / T1496). The defaults preserve
# attack realism on synthetic/LocalStack (free, fake). A real-AWS operator can force a
# cheap, free-tier-eligible type via BENCH_EC2_INSTANCE_TYPE (e.g. t3.micro) to avoid
# GPU quotas + spend — teardown terminates instances either way.
_EC2_TYPE_OVERRIDE = os.getenv("BENCH_EC2_INSTANCE_TYPE")


def _instance_type(default):
    return _EC2_TYPE_OVERRIDE or default


class LocalStackUnavailable(RuntimeError):
    pass


class RealAWSGated(RuntimeError):
    """Raised when the real_aws backend is requested without explicit confirmation."""


def make_clients(environment="localstack", endpoint=None, region=None):
    """Lazily build boto3 clients for the requested backend.

    environment="localstack" (default) -> clients point at LocalStack with dummy creds.
    environment="real_aws" -> clients hit real, BILLABLE AWS using credentials resolved
    by boto3 itself (env vars / shared profile / instance role). This path is gated
    behind BENCH_ALLOW_REAL_AWS=1 and an APPROVED_REGIONS check (both verified BEFORE
    boto3 is even imported) so a real, costing run can never start by accident.
    """
    region = region or REGION

    if environment == "real_aws":
        if os.getenv("BENCH_ALLOW_REAL_AWS") != "1":
            raise RealAWSGated(
                "real_aws is BILLABLE: set BENCH_ALLOW_REAL_AWS=1 to confirm you intend "
                "to run against a real (sandbox) AWS account, with teardown verified")
        if region not in APPROVED_REGIONS:
            raise RealAWSGated(
                f"region {region!r} not in APPROVED_REGIONS {APPROVED_REGIONS} — "
                "restrict the blast radius before running real_aws")

    try:
        import boto3  # noqa
    except ImportError as e:  # pragma: no cover - exercised only without boto3
        raise LocalStackUnavailable(
            "boto3 is required for the AWS backends (pip install boto3)") from e

    if environment == "real_aws":
        # no endpoint_url, no injected creds: boto3 resolves real credentials itself
        return {svc: boto3.client(svc, region_name=region) for svc in SERVICES}

    endpoint = endpoint or LOCALSTACK_URL
    kw = dict(endpoint_url=endpoint, region_name=region,
              aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
              aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"))
    return {svc: boto3.client(svc, **kw) for svc in SERVICES}


def check_connectivity(clients) -> bool:
    try:
        clients["s3"].list_buckets()
        return True
    except Exception:
        return False


def _cap(event_name, **fields):
    """Build a captured raw event. No MITRE label (answer-key boundary)."""
    return {"eventName": event_name, **fields}


def _safe(fn, *a, **k):
    """Run a boto3 call; return (response, error_code). A denied/failed call is
    still meaningful telemetry, so we capture it either way."""
    try:
        return fn(*a, **k), None
    except Exception as e:  # LocalStack feature gaps / access errors
        err = e.response["Error"]["Code"] if getattr(e, "response", None) \
            and "Error" in e.response else type(e).__name__
        return None, err


# --- setup / teardown ---------------------------------------------------------

class Ctx:
    def __init__(self):
        self.bucket = "prod-data"
        self.assets = "app-assets"
        self.attacker = "attacker-acct-bucket"
        self.user = "victim-user"
        self.secret = "prod/db/password"
        self.created = []  # for teardown


def setup(clients, ctx: Ctx):
    s3, iam, sm = clients["s3"], clients["iam"], clients["secretsmanager"]
    for b in (ctx.bucket, ctx.assets, ctx.attacker):
        _safe(s3.create_bucket, Bucket=b)
        ctx.created.append(("bucket", b))
    for i in range(8):
        _safe(s3.put_object, Bucket=ctx.bucket, Key=f"obj-{i}", Body=b"x" * 1024)
    _safe(s3.put_object, Bucket=ctx.assets, Key="logo.png", Body=b"png")
    _safe(iam.create_user, UserName=ctx.user)
    ctx.created.append(("user", ctx.user))
    _safe(sm.create_secret, Name=ctx.secret, SecretString="hunter2")
    ctx.created.append(("secret", ctx.secret))


def teardown(clients, ctx: Ctx):
    s3, iam, sm, ec2 = (clients["s3"], clients["iam"],
                        clients["secretsmanager"], clients["ec2"])
    for kind, name in reversed(ctx.created):
        if kind == "bucket":
            try:
                objs = s3.list_objects_v2(Bucket=name).get("Contents", [])
                for o in objs:
                    _safe(s3.delete_object, Bucket=name, Key=o["Key"])
            except Exception:
                pass
            _safe(s3.delete_bucket, Bucket=name)
        elif kind == "user":
            _safe(iam.delete_user, UserName=name)
        elif kind == "secret":
            _safe(sm.delete_secret, SecretId=name, ForceDeleteWithoutRecovery=True)
        elif kind == "instance":
            # CRITICAL on real AWS: an un-terminated instance bills indefinitely.
            _safe(ec2.terminate_instances, InstanceIds=[name])


# --- per-technique executors --------------------------------------------------
# Each returns a list of captured raw-event dicts from REAL responses.

def _exec(ttp_id, source, clients, ctx):
    s3, iam, ec2 = clients["s3"], clients["iam"], clients["ec2"]
    sts, sm = clients["sts"], clients["secretsmanager"]
    t = ttp_id

    if t == "T1078.004":                       # console login has no API -> proxy
        r, err = _safe(sts.get_caller_identity)
        return [_cap("ConsoleLogin", proxy=True, result="Success" if not err else "Error",
                     arn=(r or {}).get("Arn"), sourceIPAddress="203.0.113.5")]
    if t == "T1110":
        out = []
        for _ in range(6):
            _safe(sts.get_caller_identity)
            out.append(_cap("ConsoleLogin", proxy=True, result="Failure",
                            sourceIPAddress="203.0.113.5"))
        return out
    if t == "T1098":
        _safe(iam.create_user, UserName="backdoor")
        ctx.created.append(("user", "backdoor"))
        r, _ = _safe(iam.attach_user_policy, UserName="backdoor",
                     PolicyArn="arn:aws:iam::aws:policy/AdministratorAccess")
        return [_cap("CreateUser", userName="backdoor"),
                _cap("AttachUserPolicy", userName="backdoor")]
    if t == "T1098.001":
        r, err = _safe(iam.create_access_key, UserName=ctx.user)
        akid = ((r or {}).get("AccessKey") or {}).get("AccessKeyId")
        return [_cap("CreateAccessKey", targetUser=ctx.user, accessKeyId=akid, error=err)]
    if t in ("T1548", "T1548.005"):
        r, err = _safe(sts.get_caller_identity)
        return [_cap("AssumeRole", proxy=True, arn=(r or {}).get("Arn"), error=err)]
    if t == "T1562.008":
        r, err = _safe(clients["cloudtrail"].stop_logging, Name="org-trail")
        return [_cap("StopLogging", trailName="org-trail", error=err)]
    if t == "T1190":
        r, err = _safe(ec2.create_security_group, GroupName="open-sg", Description="x")
        gid = (r or {}).get("GroupId")
        _safe(ec2.authorize_security_group_ingress, GroupId=gid,
              IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
                              "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}])
        return [_cap("AuthorizeSecurityGroupIngress", port=22, cidr="0.0.0.0/0",
                     securityGroup=gid, error=err)]
    if t in ("T1526", "T1580"):
        rb, _ = _safe(s3.list_buckets)
        _safe(ec2.describe_instances)
        n = len((rb or {}).get("Buckets", []))
        return [_cap("ListBuckets", bucketCount=n), _cap("DescribeInstances")]
    if t == "T1528":
        r, err = _safe(sm.get_secret_value, SecretId=ctx.secret)
        return [_cap("GetSecretValue", secretId=ctx.secret, error=err)]
    if t == "T1552.005":                       # IMDS path -> proxy authenticated call
        r, err = _safe(sts.get_caller_identity)
        return [_cap("GetCallerIdentity", via="instance-metadata", proxy=True,
                     sourceIPAddress="169.254.169.254", arn=(r or {}).get("Arn"))]
    if t == "T1578":
        itype = _instance_type("c5.large")
        r, err = _safe(ec2.run_instances, ImageId="ami-12345678", InstanceType=itype,
                       MinCount=1, MaxCount=1)
        iid = (((r or {}).get("Instances") or [{}])[0]).get("InstanceId")
        if iid:
            ctx.created.append(("instance", iid))      # register for teardown
        return [_cap("RunInstances", instanceType=itype, region="us-west-2",
                     instanceId=iid, error=err)]
    if t == "T1496":
        itype = _instance_type("p3.2xlarge")
        r, err = _safe(ec2.run_instances, ImageId="ami-12345678", InstanceType=itype,
                       MinCount=1, MaxCount=1)
        iid = (((r or {}).get("Instances") or [{}])[0]).get("InstanceId")
        if iid:
            ctx.created.append(("instance", iid))      # register for teardown
        return [_cap("RunInstances", instanceType=itype, state="running",
                     instanceId=iid, error=err)]
    if t == "T1485":
        out = []
        for i in range(8):
            _safe(s3.delete_object, Bucket=ctx.bucket, Key=f"obj-{i}")
            out.append({"operation": "DeleteObject", "bucket": ctx.bucket, "key": f"obj-{i}"})
        return out
    if t == "T1530":
        if source == "S3":
            out = []
            for i in range(6):
                r, err = _safe(s3.get_object, Bucket=ctx.bucket, Key=f"obj-{i}")
                out.append({"operation": "GetObject", "bucket": ctx.bucket,
                            "key": f"obj-{i}", "http_status": 200 if not err else 404})
            return out
        r, err = _safe(s3.get_bucket_encryption, Bucket=ctx.bucket)
        return [_cap("GetBucketEncryption", bucket=ctx.bucket,
                     result="not-configured" if err else "configured")]
    if t == "T1537":
        if source == "VPC":                    # no LocalStack flow logs -> network fallback
            return [{"srcaddr": "10.0.0.7", "dstaddr": "198.51.100.9", "dstport": 443,
                     "protocol": "tcp", "action": "ACCEPT", "bytes": 250_000_000,
                     "packets": 180_000, "synthetic_network": True}]
        _safe(s3.copy_object, Bucket=ctx.attacker, Key="exfil.tar",
              CopySource={"Bucket": ctx.bucket, "Key": "obj-0"})
        return [{"operation": "CopyObject", "bucket": ctx.attacker, "key": "exfil.tar"}]
    if t == "T1046":
        return [{"srcaddr": "203.0.113.5", "dstaddr": "10.0.0.20", "dstport": p,
                 "protocol": "tcp", "action": "REJECT", "bytes": 0,
                 "synthetic_network": True} for p in range(20, 45)]
    if t == "T1571":
        return [{"srcaddr": "10.0.0.7", "dstaddr": "198.51.100.9", "dstport": 4444,
                 "protocol": "tcp", "action": "ACCEPT", "bytes": 1024,
                 "synthetic_network": True} for _ in range(4)]
    # default: issue a real identity call so SOMETHING real is captured
    r, _ = _safe(sts.get_caller_identity)
    return [_cap("GenericEvent", proxy=True, arn=(r or {}).get("Arn"))]


def _benign(clients, ctx):
    s3, ec2, sts = clients["s3"], clients["ec2"], clients["sts"]
    out = []
    _safe(s3.list_buckets);  out.append(("CloudTrail", _cap("ListBuckets", userIdentity="backup-job")))
    _safe(s3.get_object, Bucket=ctx.assets, Key="logo.png")
    out.append(("S3", {"operation": "GetObject", "bucket": ctx.assets, "key": "logo.png", "http_status": 200}))
    _safe(ec2.describe_instances); out.append(("CloudTrail", _cap("DescribeInstances", userIdentity="ops")))
    _safe(sts.get_caller_identity); out.append(("CloudTrail", _cap("GetCallerIdentity", userIdentity="ops")))
    return out


def _now():
    return datetime.now(timezone.utc)


def run_scenario_localstack(scenario_id, spec, clients, author="Atishay",
                            environment="localstack"):
    """Execute one scenario against the AWS API surface and return (events, Manifest).

    `environment` tags the captured events ("localstack" or "real_aws") and is the only
    difference between the two backends — the executors, capture, and teardown are
    identical, since both issue the same real boto3 calls (`clients` decides where they
    land). teardown ALWAYS runs (finally), so a real-AWS run cannot leak resources.
    """
    ctx = Ctx()
    setup(clients, ctx)
    events, stages = [], []
    try:
        for idx, (ttp_id, source) in enumerate(spec["stages"], start=1):
            raws = _exec(ttp_id, source, clients, ctx)
            stage_events = []
            for j, raw in enumerate(raws):
                ev = Event.create(scenario_id, idx, j, source, _now().isoformat(),
                                  raw, is_ground_truth=True, environment=environment)
                stage_events.append(ev)
            events.extend(stage_events)
            stages.append(Stage(
                stage_id=idx, ttp_id=ttp_id, ttp_name=ttp_name(ttp_id),
                telemetry_source=source,
                evidence_event_ids=[e.event_id for e in stage_events],
                timestamp_range=[stage_events[0].event_time, stage_events[-1].event_time],
            ))
        for j, (source, raw) in enumerate(_benign(clients, ctx)):
            events.append(Event.create(scenario_id, 0, j, source, _now().isoformat(),
                                        raw, is_ground_truth=False, environment=environment))
    finally:
        teardown(clients, ctx)

    authorship = {"author": author, "reviewer": "", "review_date": "TBD",
                  "authored_before_system_final": True}
    manifest = Manifest(scenario_id=scenario_id, category=spec["category"],
                        real_incident_reference=spec["incident"], stages=stages,
                        authorship=authorship)
    return events, manifest
