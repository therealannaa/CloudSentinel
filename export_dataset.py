#!/usr/bin/env python3
"""
Export the CloudKC-Bench dataset to CSV for public release.

Produces, under --out (default: dataset/):
  scenarios.csv            one row per scenario (metadata)
  events.csv               one row per event  -- the VISIBLE telemetry a detector reads
  ground_truth_stages.csv  one row per stage  -- the ANSWER KEY (techniques + evidence)
  event_labels.csv         one row per event  -- convenience event-level labels
  README.md                data dictionary + usage + the answer-key boundary

Only the development set (is_held_out = 0) is exported; the sealed hold-out is
never written, so it stays usable as a blind test.

Usage:
  python3 -m benchmark.cli --db data.db generate --set dev --environment synthetic
  python3 export_dataset.py --db data.db --out dataset/
"""
import argparse, csv, json, os, sqlite3


def event_name(raw):
    try:
        d = json.loads(raw)
    except Exception:
        return ""
    for k in ("eventName", "operation", "event_name"):
        if k in d:
            return str(d[k])
    return str(next(iter(d.values()))) if d else ""


def main():
    ap = argparse.ArgumentParser(description="Export CloudKC-Bench dataset to CSV")
    ap.add_argument("--db", default="cloudsentinel.db", help="db built by `generate`")
    ap.add_argument("--manifests", default="benchmark/manifests/dev", help="manifest JSON dir")
    ap.add_argument("--out", default="dataset", help="output directory")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    c = sqlite3.connect(args.db)

    # scenarios (dev only). real_incident_reference lives in the manifest, not
    # the table, so we read it from the manifest JSON below.
    scen_rows = list(c.execute(
        "select scenario_id, category, manifest_path from scenarios "
        "where is_held_out=0 order by scenario_id"))

    # counts per scenario
    counts = {sid: [0, 0] for (sid, _, _) in scen_rows}
    for sid, gt in c.execute("select scenario_id, is_ground_truth from events"):
        if sid in counts:
            counts[sid][0] += 1
            counts[sid][1] += int(gt or 0)

    # --- scenarios.csv ---
    with open(os.path.join(args.out, "scenarios.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "category", "real_incident_reference",
                    "n_stages", "n_events", "n_ground_truth_events"])
        n_stage_by_sid = {}
        for sid, cat, mpath in scen_rows:
            ref, nst = "", 0
            try:
                m = json.load(open(mpath))
                ref = m.get("real_incident_reference", "")
                nst = len(m.get("stages", []))
            except Exception:
                pass
            n_stage_by_sid[sid] = nst
            ne, ngt = counts.get(sid, [0, 0])
            w.writerow([sid, cat, ref, nst, ne, ngt])

    cat_by_sid = {sid: cat for (sid, cat, _) in scen_rows}

    # --- events.csv (visible telemetry only -- NO labels) ---
    with open(os.path.join(args.out, "events.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "scenario_id", "category", "source",
                    "event_time", "event_name", "raw_json"])
        for eid, sid, src, t, raw in c.execute(
            "select e.event_id, e.scenario_id, e.source, e.event_time, e.raw_json "
            "from events e join scenarios s on s.scenario_id=e.scenario_id "
            "where s.is_held_out=0 order by e.scenario_id, e.event_time, e.event_id"):
            w.writerow([eid, sid, cat_by_sid.get(sid, ""), src, t, event_name(raw), raw])

    # --- ground_truth_stages.csv (the answer key) ---
    n_stages_total = 0
    with open(os.path.join(args.out, "ground_truth_stages.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "category", "stage_id", "ttp_id", "ttp_name",
                    "telemetry_source", "evidence_event_ids", "ts_start", "ts_end"])
        # event_id -> (stage_id, ttp_id) for the labels file
        ev_label = {}
        for sid, cat, mpath in scen_rows:
            try:
                m = json.load(open(mpath))
            except Exception:
                continue
            for s in m.get("stages", []):
                ev_ids = s.get("evidence_event_ids", [])
                tr = s.get("timestamp_range", ["", ""])
                w.writerow([sid, cat, s.get("stage_id"), s.get("ttp_id"),
                            s.get("ttp_name"), s.get("telemetry_source"),
                            ";".join(ev_ids), tr[0], tr[1] if len(tr) > 1 else ""])
                n_stages_total += 1
                for e in ev_ids:
                    ev_label[e] = (s.get("stage_id"), s.get("ttp_id"))

    # --- event_labels.csv (convenience event-level labels) ---
    n_ev = 0
    with open(os.path.join(args.out, "event_labels.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event_id", "scenario_id", "is_attack_event", "stage_id", "ttp_id"])
        for eid, sid, gt in c.execute(
            "select e.event_id, e.scenario_id, e.is_ground_truth from events e "
            "join scenarios s on s.scenario_id=e.scenario_id where s.is_held_out=0 "
            "order by e.scenario_id, e.event_id"):
            st, ttp = ev_label.get(eid, ("", ""))
            w.writerow([eid, sid, int(gt or 0), st, ttp])
            n_ev += 1

    # --- README.md (data dictionary) ---
    n_scen = len(scen_rows)
    with open(os.path.join(args.out, "README.md"), "w") as f:
        f.write(README.format(n_scen=n_scen, n_ev=n_ev, n_stages=n_stages_total))

    print(f"Exported to {args.out}/: {n_scen} scenarios, {n_ev} events, "
          f"{n_stages_total} ground-truth stages.")


README = """# CloudKC-Bench Dataset (CSV release)

Open dataset for **AWS control-plane multi-stage kill-chain reconstruction**.
This release contains the development set: **{n_scen} scenarios, {n_ev} events,
{n_stages} ground-truth stages**. The sealed hold-out set is *not* included, so it
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
"""

if __name__ == "__main__":
    main()
