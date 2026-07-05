# Failure-Mode Analysis — Plan (C4)

**Owner:** shared | **Status:** PLAN — executed in **P4/P5** (cannot be written until experiments complete).

> **Why this document exists (plain language).** This is the section that turns a "we measured it" workshop
> paper into a "here's *when and why* it works or fails" journal paper (v3 §9, contribution C4). It can't be
> written until the runs are done — but the data it needs must be **logged from the start**. This plan fixes
> *what the benchmark runner must capture in P3/P4* so the analysis is possible later.

---

## 1. What the analysis will report (v3 §9.1)

- **Per-category breakdown:** where does each arm fail most? Is failure consistent across arms (hard scenario)
  or arm-specific (structural weakness of one approach)?
- **Per-ATT&CK-technique breakdown:** which TTPs (e.g. `T1078` Valid Accounts, `T1530` Data from Cloud
  Storage) are consistently missed? Which technique *combinations* break cross-domain correlation?
- **False-positive characterisation:** are FPs random noise or systematic (e.g. benign admin IAM activity
  firing privilege-escalation alerts)? Use the `BN-*` benign scenarios.
- **LLM-specific failure modes:** hallucinated stage attributions; events missed because they fell outside the
  context window; over-correlation of noisy benign events. Document with concrete examples from runs.
- **Pre-filter recall stress:** on `LS-*` (low-and-slow), how often does the pre-filter discard ground-truth
  evidence before the LLM sees it? Report as an explicit failure mode with counts.

## 2. What the runner must log so this is possible (P3/P4 requirement)

These feed off the `05` schema; confirm each is captured:

- Per-run, per-stage **match outcome** (TP/FP/FN) with the cited vs ground-truth `evidence_event_ids` (from
  the matching function `04`) → enables per-technique and per-category breakdowns.
- **Pre-filter decisions** per event (`events.pre_filter_passed`) cross-referenced with
  `events.is_ground_truth` → pre-filter recall stress directly.
- **Raw agent outputs** (`agent_outputs`) → lets us inspect LLM hallucinations/over-correlation post-hoc.
- **Arm + environment + seed** on every run (`runs`) → separates arm-specific vs scenario-hard failure, and
  real-AWS vs LocalStack differences.

## 3. Why it matters either way (v3 §9.2)

- If **H1 is supported** (LLM beats rules): this section tells practitioners *when not to trust* the LLM.
- If **H1 fails** (LLM doesn't beat rules): explaining *why* becomes the paper's **main analytical
  contribution** — more interesting than the bare negative result.

No content is written here in P1 beyond this plan; the data-capture requirements are the actionable part.
