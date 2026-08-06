#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CloudKC-Bench — narrated live demo (offline, no AWS, no GPU required).
#
#   ./demo.sh              # interactive: pauses between steps for narration
#   PAUSE=0 ./demo.sh      # run straight through (for recording / dry-run)
#
# Uses the synthetic backend and the rules arm (A4) + the two scoring lenses,
# so the whole thing runs on a laptop. The LLM arms (A1-A3) need Ollama; see
# the closing note for how to show those from the already-captured real run.
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

DB="demo.db"
CAT="multi_stage_kill_chain"
SCEN="KC-01"
PAUSE="${PAUSE:-1}"

bold=$'\e[1m'; dim=$'\e[2m'; cyan=$'\e[36m'; green=$'\e[32m'; reset=$'\e[0m'

hr()    { printf '%s\n' "${cyan}────────────────────────────────────────────────────────────${reset}"; }
say()   { printf '%s\n' "${bold}$*${reset}"; }
note()  { printf '%s\n' "${dim}$*${reset}"; }
pause() { [ "$PAUSE" = "1" ] && { printf '%s' "${dim}  (press Enter)${reset}"; read -r _ || true; } || true; }

hr; say "CloudKC-Bench — live demo"
note "An open benchmark for reconstructing AWS multi-stage kill chains."
note "Everything below runs offline on the synthetic backend."; hr; pause

# --- 0. the pipeline works -------------------------------------------------
say "① Sanity check — the whole pipeline, end to end"
note "Generates scenarios, seals the hold-out, and tests the scoring function."
python3 -m benchmark.cli selfcheck
pause; hr

# --- 1. build the benchmark ------------------------------------------------
say "② Generate the benchmark (59 dev scenarios, five categories)"
rm -f "$DB"
ENVIRONMENT=synthetic python3 -m benchmark.cli --db "$DB" generate --set dev --environment synthetic
python3 -m benchmark.cli --db "$DB" summary
pause; hr

# --- 2. the answer-key boundary --------------------------------------------
say "③ The answer-key boundary — what a detector sees vs. the hidden truth"
note "First, the VISIBLE telemetry for scenario ${SCEN} (this is all a detector reads):"
python3 - "$DB" "$SCEN" <<'PY'
import sqlite3, json, sys
db, scen = sys.argv[1], sys.argv[2]
c = sqlite3.connect(db)
for eid, src, t, raw in c.execute(
    "select event_id, source, event_time, raw_json from events "
    "where scenario_id=? order by event_time", (scen,)):
    d = json.loads(raw)
    name = d.get("eventName") or d.get("operation") or next(iter(d.values()))
    print(f"  {t[11:19]}  {src:11} {name:18} {eid}")
PY
echo
note "Notice: every line looks like an ordinary administrative action —"
note "no technique labels anywhere. Now the HIDDEN manifest (the answer key):"
python3 - "$SCEN" <<'PY'
import json, sys
m = json.load(open(f"benchmark/manifests/dev/{sys.argv[1]}.json"))
print(f"  incident: {m['real_incident_reference']}")
for s in m["stages"]:
    print(f"  stage {s['stage_id']}: {s['ttp_id']:11} {s['ttp_name']:45} <- {','.join(s['evidence_event_ids'])}")
PY
echo
note "The SAME events carry the attack — but the technique labels (T1078, T1098,"
note "T1530 ...) live only in the manifest, which no detector is allowed to read."
pause; hr

# --- 3. run a detector and score it ----------------------------------------
say "④ Run a detector over the scenarios and score it (rules arm A4)"
note "Model, telemetry, and compute are held fixed — only the arm changes."
python3 -m benchmark.cli --db "$DB" run-arms --arms A4 --category "$CAT" --csv demo_scores.csv
pause; hr

# --- 4. the two lenses ------------------------------------------------------
say "⑤ Score under the two lenses"
note "Event lens: did it FIND the attack events?"
python3 -m benchmark.cli --db "$DB" detection
echo
note "Technique lens: did it NAME each technique correctly? (watch the confusions)"
python3 -m benchmark.cli --db "$DB" confusion
pause; hr

# --- 5. where to go next ----------------------------------------------------
say "⑥ The LLM arms and the full study"
note "The A1-A3 language-model arms need Ollama:  ./run_ollama.sh"
note "To show the real Qwen results without re-running the cloud, replay the"
note "captured run:"
note "    python3 -m benchmark.cli --db real.db analyze     # H1/H2 verdicts + CIs"
note "    python3 make_paper_outputs.py                     # regenerate the figures"
hr; say "${green}Demo complete.${reset}"
