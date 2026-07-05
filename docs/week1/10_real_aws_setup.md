# Real-AWS Sandbox Setup & Budget

**Owner:** shared | **Status:** 🚧 **NOT STARTED UNTIL BUDGET APPROVED** (v3 §14.2, blocking)

> **Why this document exists (plain language).** v3 makes **real AWS** the primary environment for external
> validity — a journal reviewer will not accept LocalStack alone for a security-detection paper. But real AWS
> costs money and needs supervisor budget sign-off, so we document the setup now and *execute it only after
> approval*. Until then, all development happens on LocalStack (the gated-milestone approach).

---

## 1. Account & isolation (v3 §5.2)

- **Dedicated sandbox account** — a fresh AWS account (or sub-account under an Organization), used *only* for
  this research. **Never** a personal or production account.
- **Scoped IAM** — a per-category IAM role/user with the minimum permissions to execute that scenario
  category. Rotate credentials after each test campaign. (Reuse the least-privilege thinking already in
  `config.py` / `tools/baseline.py`.)
- **Safety boundary** — attacks run **only** against infrastructure inside this sandbox account. No third-party
  targets, nothing outside the account. This is legitimate own-account security research.

## 2. GuardDuty (primary external baseline, `11`)

- Enable GuardDuty on the sandbox account.
- **Documented warm-up:** ≥ 7 days of baseline traffic before running attack scenarios, so findings reflect a
  realistic detection environment. Record the warm-up window in the results.

## 3. Teardown (mandatory)

- A **teardown script** destroys every resource a scenario created (IAM users/roles, EC2, S3 buckets, Lambda,
  snapshots/AMIs) after each run. Verify it runs clean (no orphaned resources, no lingering cost).
- Teardown verification is part of each scenario's run record.

## 4. Cost estimate & budget (FILL, then supervisor sign-off)

Scope: ~70 scenarios × 4 arms × S seeds, plus GuardDuty + LLMCloudHunter baseline runs. LLM token cost is
tracked separately (`14_cost_latency_plan.md`); this table is **AWS infrastructure** cost.

| Cost driver | Unit assumption | Qty | Est. unit cost | Est. total |
|-------------|-----------------|-----|----------------|------------|
| EC2 (incl. ephemeral/mining-shape instances) | per scenario-run hour | _ | _ | _ |
| S3 (storage + requests) | per scenario-run | _ | _ | _ |
| Data transfer (exfil-simulating egress) | per GB | _ | _ | _ |
| GuardDuty (events analysed) | per month + per-event | _ | _ | _ |
| CloudTrail / VPC Flow Logs delivery | per scenario-run | _ | _ | _ |
| **Total (with safety margin ×1.5)** | | | | **_** |

- **Spend cap & owner:** `______` (who approves overruns).
- **Tracking:** AWS Budgets alert at 50/80/100% of cap; reconcile actual vs estimate weekly.

## 5. Dual-environment reporting (v3 §5.3)

| Environment | Role |
|-------------|------|
| Real AWS sandbox | **Primary** — headline results, real telemetry, GuardDuty comparison |
| LocalStack | **Reproducibility layer** — others rerun without an AWS account; consistency check |

Real-AWS numbers are the headline; LocalStack numbers are reported alongside as the reproducibility check.

## Gate

Do not provision anything in this document until items 9 (budget) and 8 (venue) of
`07_sync_checkpoint_agenda.md` are signed off. Development proceeds on LocalStack regardless.
