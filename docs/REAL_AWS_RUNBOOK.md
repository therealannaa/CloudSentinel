# Real-AWS Run Runbook (with GuardDuty)

**Audience:** the teammate executing the real-AWS campaign. **Goal:** run CloudKC-Bench against a real
(sandbox) AWS account, capture real telemetry, run the arms + GuardDuty, and tear everything down with
near-zero cost. Follow the phases in order. Every command is copy-pasteable; replace `<...>` placeholders.

> **Planning context** (budget rationale, dual-environment reporting) lives in
> [`docs/week1/10_real_aws_setup.md`](week1/10_real_aws_setup.md). This file is the *operational* how-to.

---

## TL;DR of the flow

1. Fresh **sandbox AWS account** → budget alarm → scoped IAM user with **long-lived keys** (not temporary creds).
2. **Enable GuardDuty first** (it needs a ≥7-day warm-up; the 30-day free trial covers the whole campaign).
3. Set env vars (region lock + `t3.micro` override + `BENCH_ALLOW_REAL_AWS=1` + `OLLAMA_KEEP_ALIVE=-1`).
4. `generate --environment real_aws --resume` → captures telemetry against AWS **once**, auto-tears-down, restartable.
5. Warm the model, then `run-arms --environment real_aws --resume` → arms over captured events, **offline**, restartable.
6. `analyze` / `detection` / `confusion` / `failures` → the numbers.
7. Export **GuardDuty findings**, compare to ground truth.
8. **Teardown verification** → confirm zero orphaned resources → disable GuardDuty → stop recurring charges.

---

## ⚠️ Five cost/data traps — read before anything else

These are real, confirmed in the code. Ignoring them either burns money or silently corrupts the run.

1. **Always set `BENCH_EC2_INSTANCE_TYPE=t3.micro`.** Two techniques (T1578, T1496) call `RunInstances`.
   T1496's *default* is `p3.2xlarge` — a GPU instance at **~$3+/hour**. The override in Phase 3 forces the
   cheap free-tier-eligible type for both. Do not skip it.
2. **`RunInstances` uses a placeholder AMI (`ami-12345678`) that does not exist on real AWS.** So on real AWS
   those two calls **fail with `InvalidAMIID.NotFound`** and no instance launches. Good news: this means EC2
   cannot accidentally bill you out of the box. Bad news: T1578/T1496 telemetry will be an *error event*, not a
   realistic launch. If you want faithful EC2 telemetry, ask Atishay to add a `BENCH_AMI_ID` env var (small
   change; not done yet) and supply a real free-tier AMI id for `ap-south-1`. Otherwise, note this gap in the run log.
3. **GuardDuty has no automated scoring in this repo.** The benchmark scores the *arms* (A1–A4/SIGMA)
   automatically; GuardDuty is enabled and its findings are exported/compared **manually** (Phase 7). Budget
   time for that. Don't expect `analyze` to produce a GuardDuty number.
4. **Cold-model reload aborts a combined run.** Running capture + arms as one command leaves Ollama idle for the
   1–2 h capture; the default 5-min keep-alive unloads the 32B, and the first arm call then cold-loads ~20 GB and
   times out. Fix: `OLLAMA_KEEP_ALIVE=-1`, split into two phases, and warm the model between them (Phase 6).
5. **Expiring credentials silently poison the capture.** Temporary creds (SSO/`assume-role`, i.e. anything with
   an `AWS_SESSION_TOKEN`) expire at ~1 h; when they lapse mid-capture the `_safe()` guard records error
   telemetry instead of crashing. Use long-lived IAM user keys and clear stale session env vars (Phase 3).

---

## Phase 0 — Local prerequisites (on the machine running the benchmark)

```bash
# AWS CLI v2
aws --version                     # if missing: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

# Python deps incl. boto3 (real backends need it)
pip install -r requirements.txt   # NOT requirements-bench.txt — that one omits boto3

# LLM backend for the arms (runs locally; no AWS cost). Match the 32b campaign:
ollama pull qwen2.5:32b           # or your chosen model; see README "Run with a local model"
```

---

## Phase 1 — Sandbox account + isolation

Use a **dedicated AWS account** that holds nothing else. Never a personal or production account. Cleanest
option: an Organizations member account created just for this study; a standalone free-tier account also works.

**Region:** the code defaults to `ap-south-1` (Mumbai) and refuses any other region unless you widen
`APPROVED_REGIONS`. Keep everything in `ap-south-1`.

**Create a scoped IAM user for the benchmark** (console → IAM → Users, or CLI from an admin session):

```bash
aws iam create-user --user-name cloudsentinel-bench
aws iam create-access-key --user-name cloudsentinel-bench   # save AccessKeyId + SecretAccessKey
```

Attach a scoped policy (create `bench-policy.json` with the block below, then attach). This covers exactly the
services the benchmark touches plus GuardDuty and cost/billing reads:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow",
      "Action": ["s3:*", "ec2:*", "sts:*", "secretsmanager:*", "cloudtrail:*",
                 "guardduty:*", "budgets:*", "ce:Get*", "cloudwatch:*"],
      "Resource": "*" },
    { "Effect": "Allow",
      "Action": ["iam:CreateUser", "iam:DeleteUser", "iam:AttachUserPolicy",
                 "iam:DetachUserPolicy", "iam:PutUserPolicy", "iam:DeleteUserPolicy",
                 "iam:CreateAccessKey", "iam:DeleteAccessKey", "iam:ListUsers",
                 "iam:ListAccessKeys", "iam:GetUser"],
      "Resource": "*" }
  ]
}
```

```bash
aws iam put-user-policy --user-name cloudsentinel-bench \
  --policy-name cloudsentinel-bench --policy-document file://bench-policy.json
```

> This is broad-but-sandboxed (`s3:*` etc.) for convenience in a throwaway account. In a shared org, tighten to
> the specific resource ARNs the scenarios use.

**Configure the CLI profile** the benchmark's boto3 will resolve credentials from:

```bash
aws configure --profile cloudsentinel-sandbox
#   AWS Access Key ID:     <from create-access-key>
#   AWS Secret Access Key: <from create-access-key>
#   Default region name:   ap-south-1
#   Default output format:  json
```

---

## Phase 2 — Cost guardrails (do this before spending anything)

**A. Budget with alerts** (console is easiest: Billing → Budgets → Create budget → Cost budget → e.g. **$20**
monthly → alerts at 50/80/100% to your email). CLI equivalent, save as `budget.json` and `notif.json`:

```bash
# budget.json
{ "BudgetName": "cloudsentinel-sandbox", "BudgetLimit": {"Amount": "20", "Unit": "USD"},
  "TimeUnit": "MONTHLY", "BudgetType": "COST" }
```
```bash
aws budgets create-budget --account-id <ACCOUNT_ID> \
  --budget file://budget.json \
  --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"<you@example.com>"}]}]'
```

**B. Confirm free-tier / trial windows.** GuardDuty gives a **30-day free trial per account+region** — plan to
finish the GuardDuty part inside that window. S3/IAM/STS/SecretsManager usage here is tiny (KB objects,
force-deleted secrets, seconds of activity).

---

## Phase 3 — Environment variables (the safety + cost switches)

Run these in the shell you'll launch the benchmark from. **All of them matter.**

```bash
export AWS_PROFILE=cloudsentinel-sandbox      # boto3 resolves creds from this profile
export AWS_DEFAULT_REGION=ap-south-1
export APPROVED_REGIONS=ap-south-1            # blast-radius guard; run refuses other regions
export BENCH_ALLOW_REAL_AWS=1                 # explicit "yes, bill me" gate (required for real_aws)
export BENCH_EC2_INSTANCE_TYPE=t3.micro       # TRAP #1 fix — forces cheap instance type

# LLM backend for the arms (local Ollama; no AWS cost):
export LLM_BASE_URL=http://localhost:11434/v1
export LLM_API_KEY=ollama
export LLM_MODEL=qwen2.5:32b
export OLLAMA_KEEP_ALIVE=-1                   # TRAP #4 fix — keep the model resident (see Phase 6)
```

Without `BENCH_ALLOW_REAL_AWS=1` or with a region outside `APPROVED_REGIONS`, the backend raises `RealAWSGated`
and nothing runs — that is the intended safety behavior.

> **Windows/PowerShell:** use `$env:NAME="value"` instead of `export`. On Windows the operator typically runs
> from PowerShell — set `OLLAMA_KEEP_ALIVE` for the **Ollama server** (then restart Ollama), not just the shell.

**⚠️ Credential longevity (TRAP #5 — silent data poisoning).** A full `--set all` capture takes 1–2 hours.
**Temporary** credentials (SSO / `assume-role` / anything with an `AWS_SESSION_TOKEN`) expire at ~1 h by
default; when they lapse mid-capture, every AWS call is caught by the backend's `_safe()` guard and recorded as
*error telemetry* — the run does **not** crash, it silently produces a poisoned second half. LocalStack never
hits this because its dummy `test`/`test` creds never expire. Use **long-lived IAM user access keys** from the
sandbox account (Phase 1 creates them) and make sure no stale temporary creds override the profile:

```bash
aws sts get-caller-identity      # Arn should be .../user/cloudsentinel-bench, NOT .../assumed-role/...
echo "$AWS_SESSION_TOKEN"         # must be EMPTY; if set, you're on temporary creds
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN   # env-var creds override the profile
```
```powershell
# PowerShell equivalent:
Remove-Item Env:AWS_ACCESS_KEY_ID, Env:AWS_SECRET_ACCESS_KEY, Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue
```
If you must use a role, raise its session: `aws iam update-role --role-name <R> --max-session-duration 43200`
then `assume-role --duration-seconds 43200` (12 h). Long-lived user keys are simpler and never expire.

---

## Phase 4 — Enable GuardDuty and start the warm-up (do this ~1 week early)

GuardDuty needs baseline traffic before it detects well. Enable it, then let it sit ≥7 days **before** running
the attack scenarios so findings reflect a realistic environment.

```bash
aws guardduty create-detector --enable --region ap-south-1
#   -> { "DetectorId": "abc123..." }  <-- save this

# confirm it's on and note the free-trial end date:
aws guardduty get-detector --detector-id <DETECTOR_ID> --region ap-south-1
```

Record the warm-up start time in your run log. During warm-up you can do the account setup and a LocalStack
dry-run (below), but do **not** run `generate --environment real_aws` yet.

---

## Phase 5 — Dry-run on LocalStack (free rehearsal — strongly recommended)

Prove the whole pipeline works against fake AWS before spending a cent. LocalStack accepts the same code path.

```bash
docker compose up -d
python -m benchmark.cli localstack-check          # -> REACHABLE
python -m benchmark.cli --db dryrun.db generate --set all --environment localstack
python -m benchmark.cli --db dryrun.db run-arms --set all --environment localstack
docker compose down
```

If that completes cleanly, the real-AWS run will behave the same (minus the AMI caveat, Trap #2).

---

## Phase 6 — The real-AWS run (after the ≥7-day GuardDuty warm-up)

**Run capture and arms as two separate, resumable phases — do NOT combine them into one command.** A
`--set all` real-AWS capture runs 1–2 hours; the LLM arms are another multi-hour local job. Splitting them
means a crash in either phase never loses the other's work, and it avoids the failure below.

> **TRAP #4 — cold-model reload after a long capture.** If you run capture and arms as one command, Ollama sits
> **idle for the whole 1–2 h capture** and (with the default 5-minute keep-alive) unloads the 32B model. When
> the arms then start, the first call cold-loads ~20 GB and blows past the read timeout → the run aborts
> "1–2 h in." Fixes, both applied below: set `OLLAMA_KEEP_ALIVE=-1` (Phase 3) so the model stays resident, and
> **warm the model right before the arms**. This is why LocalStack "just works" — its capture is instant, so
> there's no idle gap.

Use a **fresh DB named for this experiment** so results never mix with other models/environments.

```bash
# STEP 1 — capture real-AWS telemetry ONCE, RESUMABLE. This is the only step that touches (and bills) AWS.
#   --resume skips scenarios already captured in the DB, so a crashed capture restarts where it left off
#   (only the missing scenarios re-hit the API) instead of redoing hours of work.
python -m benchmark.cli --db qwen32b_realaws.db generate --set all --environment real_aws --resume

# Between phases: keep the model resident and warm it so the first arm call isn't a cold 20 GB load.
export OLLAMA_KEEP_ALIVE=-1                              # (already set in Phase 3; restart Ollama if you set it late)
ollama run qwen2.5:32b-instruct-q4_k_m "ready"          # warm-up ping

# STEP 2 — run the arms over captured events, RESUMABLE. OFFLINE (local LLM) — no AWS, no cost.
#   --resume skips (arm, scenario, seed) combinations already scored, so if Ollama dies mid-run you just
#   re-run this exact line and it continues from where it stopped.
python -m benchmark.cli --db qwen32b_realaws.db run-arms --set all --environment real_aws --resume \
  --csv results_qwen32b_realaws.csv
```

Notes:
- **Step 2 never touches AWS.** Because the scenarios are already in the DB, `run-arms` does not auto-generate,
  so AWS credentials, throttling, and teardown flakiness are irrelevant to the arms — only Step 1 needs creds.
- **Always run Step 1 explicitly first.** If you skip it, `run-arms` will auto-generate against real AWS on its
  own; running Step 1 separately keeps AWS execution to exactly one controlled pass.
- **If a phase crashes,** just re-run the same command with `--resume` — Step 1 skips captured scenarios, Step 2
  skips scored runs. Neither redoes completed work.
- The captured `RunInstances` events (T1578/T1496) will carry an AMI error unless Trap #2 is addressed.

---

## Phase 7 — Analysis (arms) + GuardDuty comparison (manual)

**Arms (automated), tagged to the real-AWS environment:**

```bash
python -m benchmark.cli --db qwen32b_realaws.db analyze --environment real_aws --ttp-match parent --csv analyze_realaws.csv
python -m benchmark.cli --db qwen32b_realaws.db detection --environment real_aws --csv detection_realaws.csv
python -m benchmark.cli --db qwen32b_realaws.db confusion --environment real_aws --csv confusion_realaws.csv
python -m benchmark.cli --db qwen32b_realaws.db failures  --environment real_aws --csv failures_realaws.csv
```

**GuardDuty (manual):** during/after step 6, GuardDuty accrues findings on the attack activity. Export them:

```bash
# list finding ids
aws guardduty list-findings --detector-id <DETECTOR_ID> --region ap-south-1 > gd_ids.json

# pull full findings (feed the ids from gd_ids.json into --finding-ids)
aws guardduty get-findings --detector-id <DETECTOR_ID> --region ap-south-1 \
  --finding-ids <id1> <id2> ... > guardduty_findings.json
```

Then compare `guardduty_findings.json` to the ground-truth manifests by **timestamp + resource (bucket / user /
instance)**: for each scenario, did GuardDuty raise a relevant finding, and does its type roughly map to the
ATT&CK technique? This is a manual/semi-manual mapping — there is no scoring code for GuardDuty yet. Capture it
as a table (scenario, GuardDuty finding type, detected Y/N, notes) for the paper's external-baseline section.

---

## Phase 8 — Teardown verification (mandatory — this is what stops the bill)

The benchmark tears down each scenario's resources automatically (in a `finally`), but **verify** nothing
leaked, then stop the recurring services.

```bash
# 1) No running/pending instances (the only thing that bills by the hour):
aws ec2 describe-instances --region ap-south-1 \
  --filters "Name=instance-state-name,Values=running,pending" \
  --query "Reservations[].Instances[].InstanceId"

# 2) No leftover benchmark buckets (expect: none of prod-data / app-assets / attacker-acct-bucket):
aws s3 ls

# 3) No leftover benchmark IAM users (expect: no victim-user / backdoor):
aws iam list-users --query "Users[].UserName"

# 4) No leftover secrets (expect: no prod/db/password):
aws secretsmanager list-secrets --region ap-south-1 --query "SecretList[].Name"

# 5) No leftover security groups named open-sg:
aws ec2 describe-security-groups --region ap-south-1 \
  --query "SecurityGroups[?GroupName=='open-sg'].GroupId"
```

If any of the above returns resources, delete them manually before proceeding.

**Stop recurring charges:**

```bash
# disable GuardDuty (stops per-event analysis charges after the free trial):
aws guardduty delete-detector --detector-id <DETECTOR_ID> --region ap-south-1

# if you created a CloudTrail trail for realism, delete it too:
aws cloudtrail list-trails --region ap-south-1
# aws cloudtrail delete-trail --name <trail-name> --region ap-south-1
```

**Final cost check** (next day, since billing lags):

```bash
aws ce get-cost-and-usage --time-period Start=<YYYY-MM-01>,End=<YYYY-MM-DD> \
  --granularity DAILY --metrics "UnblendedCost" --region us-east-1
```
(Cost Explorer is a global/us-east-1 endpoint.) Reconcile against the budget from Phase 2.

---

## Cost cheat-sheet

| Service | What the benchmark does | Real-AWS cost |
|---|---|---|
| S3 | 3 tiny buckets, KB objects, list/get/copy/delete | effectively $0 (free tier) |
| IAM / STS | create/delete users, access keys, GetCallerIdentity | free |
| Secrets Manager | 1 secret/scenario, force-deleted immediately | ~$0 (prorated, seconds of life) |
| EC2 | `RunInstances` — **fails on the placeholder AMI** (Trap #2) | $0 unless you supply a real AMI; then `t3.micro` ≈ free tier |
| CloudTrail | `StopLogging` call (errors w/o a trail) | management events free |
| VPC Flow Logs | network events are `synthetic_network` fallbacks | $0 (not real flow logs) |
| **GuardDuty** | analyzes CloudTrail/DNS during the run | **$0 within the 30-day free trial**; otherwise ~$/million events |
| LLM (arms) | qwen via local Ollama | $0 (local) |

Realistic total for one full `--set all` campaign inside the GuardDuty free trial: **a few dollars at most**,
dominated by nothing in particular. The budget alarm at $20 is a comfortable ceiling.

---

## Known gaps to flag in the run log / paper

- **AMI placeholder (Trap #2):** T1578/T1496 don't launch real instances on AWS as-is. Either accept
  error-telemetry for those two, or get `BENCH_AMI_ID` added first.
- **GuardDuty scoring is manual (Trap #3):** no code path; document the mapping methodology you used.
- **VPC Flow Logs remain synthetic fallbacks** even on real AWS (LocalStack limitation carried over); real
  network telemetry is the Zeek/flow-logs item in the broader plan.
- **CloudTrail `org-trail`** doesn't exist by default, so T1562.008 records an error event unless you
  pre-create a trail named `org-trail`.
