# CloudKC-Bench Dataset (CSV release)

Open dataset for **AWS control-plane multi-stage kill-chain reconstruction**.
This release contains the development set: **59 scenarios, 487 events,
88 ground-truth stages**. The sealed hold-out set is *not* included, so it
remains a valid blind test.

## Files

| File | Grain | Role |
|---|---|---|
| `scenarios.csv` | one row per scenario | metadata |
| `events.csv` | one row per event | **visible telemetry** — the only data a detector may read |
| `ground_truth_stages.csv` | one row per stage | **answer key** — technique + evidence per stage |
| `event_labels.csv` | one row per event | convenience event-level labels (derived) |

## The answer-key boundary (important)

`events.csv` carries **no labels**. An attacker's API call and a routine
administrative call look identical in the visible telemetry; the technique label
lives only in `ground_truth_stages.csv`. To evaluate a detector fairly, read only
`events.csv`, produce a reconstructed chain, then score it against the answer key.
Do **not** train or condition a detector on `event_labels.csv` /
`ground_truth_stages.csv` — that is the label it is meant to predict.

## Columns

**scenarios.csv** — `scenario_id`, `category`, `real_incident_reference`,
`n_stages`, `n_events`, `n_ground_truth_events`.

**events.csv** — `event_id`, `scenario_id`, `category`, `source`
(CloudTrail | VPC | S3 | EC2), `event_time` (ISO-8601), `event_name`,
`raw_json` (full event payload).

**ground_truth_stages.csv** — `scenario_id`, `category`, `stage_id`, `ttp_id`
(MITRE ATT&CK technique, e.g. T1078.004), `ttp_name`, `telemetry_source`,
`evidence_event_ids` (semicolon-separated, joining to `events.event_id`),
`ts_start`, `ts_end`.

**event_labels.csv** — `event_id`, `scenario_id`, `is_attack_event` (0/1),
`stage_id`, `ttp_id`.

## Categories

`single_domain`, `multi_stage_kill_chain`, `low_and_slow`, `ephemeral`, `benign`
(the benign category has no ground-truth stages; any flagged event there is a
false alarm).

## Joining

`events.event_id` ↔ `ground_truth_stages.evidence_event_ids` (split on `;`) and
↔ `event_labels.event_id`. All three share `scenario_id`.

## Citation & license

Please cite the CloudKC-Bench paper. Released for research use; see the repository
LICENSE. Regenerate deterministically with the synthetic backend:
`python3 -m benchmark.cli --db data.db generate --set dev --environment synthetic`.
