#!/usr/bin/env python3
"""Task-specific reliability metrics for kill-chain reconstruction, from the run DBs.

Metrics (per arm, multi-stage):
  - hallucination rate : proposals naming a technique outside the benchmark vocabulary
  - detection success  : fraction of scenarios where >=1 true attack event was flagged
  - full-chain success : fraction of scenarios reconstructed with recall == 1.0
  - technique-exact    : fraction of ground-truth events labeled with the exact technique
  - tactic accuracy    : fraction labeled with a technique sharing the true technique's tactic
Outputs: paper/tables/tab11_taskspecific.csv
"""
import sqlite3, json, os
from collections import defaultdict
from benchmark.simulator.builder import build_scenario
from benchmark.simulator.specs import SCENARIO_SPECS
from benchmark.arms.llm_client import _technique_menu

ROOT = os.path.dirname(os.path.abspath(__file__))
TAB = os.path.join(ROOT, "paper/tables")
VOCAB = set(_technique_menu().replace(" ", "").split(","))

TAC = {
 'T1046':{'Discovery'},'T1078':{'InitialAccess','Persistence','PrivEsc','DefEvasion'},
 'T1078.004':{'InitialAccess','Persistence','PrivEsc','DefEvasion'},'T1098':{'Persistence'},
 'T1098.001':{'Persistence'},'T1110':{'CredAccess'},'T1190':{'InitialAccess'},'T1485':{'Impact'},
 'T1496':{'Impact'},'T1526':{'Discovery'},'T1528':{'CredAccess'},'T1530':{'Collection'},
 'T1537':{'Exfiltration'},'T1548':{'PrivEsc','DefEvasion'},'T1548.005':{'PrivEsc','DefEvasion'},
 'T1552.005':{'CredAccess'},'T1562.001':{'DefEvasion'},'T1562.008':{'DefEvasion'},
 'T1571':{'C2'},'T1578':{'DefEvasion'},'T1580':{'Discovery'},'T1595':{'Recon'}}
def tac(t): return TAC.get(t, TAC.get(t.split('.')[0], set()))

# true technique per event, from locally-rebuilt manifests (event IDs match the DBs)
TRUE = {}
for sid, spec in SCENARIO_SPECS.items():
    _, m = build_scenario(sid, spec)
    TRUE[sid] = {eid: st['ttp_id'] for st in m.to_dict()['stages'] for eid in st['evidence_event_ids']}


def compute(db):
    c = sqlite3.connect(db)
    gt = defaultdict(set)
    for sid, eid in c.execute("SELECT scenario_id,event_id FROM events WHERE is_ground_truth=1"):
        gt[sid].add(eid)
    runs = c.execute("SELECT r.run_id,r.arm,r.scenario_id,s.category,sc.recall FROM runs r "
                     "JOIN scenarios s ON s.scenario_id=r.scenario_id "
                     "LEFT JOIN scores sc ON sc.run_id=r.run_id WHERE r.environment='real_aws'").fetchall()
    H = defaultdict(lambda: [0, 0]); D = defaultdict(lambda: [0, 0]); F = defaultdict(lambda: [0, 0])
    TE = defaultdict(lambda: [0, 0]); TAcc = defaultdict(lambda: [0, 0])
    for run_id, arm, sid, cat, rec in runs:
        if cat != 'multi_stage_kill_chain':
            continue
        # hallucination: raw proposals outside vocab
        for (oj,) in c.execute("SELECT output_json FROM agent_outputs WHERE run_id=?", (run_id,)):
            for p in (json.loads(oj) if oj else []):
                H[arm][1] += 1
                if p.get('ttp_id') not in VOCAB: H[arm][0] += 1
        # reconstructed assignment per event
        recon, assigned = set(), {}
        for tt, ev in c.execute("SELECT ttp_id,evidence_event_ids FROM reconstructed_stages WHERE run_id=?", (run_id,)):
            for eid in json.loads(ev):
                recon.add(eid); assigned[eid] = tt
        D[arm][1] += 1; D[arm][0] += 1 if recon & gt[sid] else 0
        F[arm][1] += 1; F[arm][0] += 1 if (rec or 0) >= 0.999 else 0
        for eid, tt in TRUE[sid].items():
            TE[arm][1] += 1; TAcc[arm][1] += 1
            a = assigned.get(eid)
            if a == tt: TE[arm][0] += 1
            if a and (tac(a) & tac(tt)): TAcc[arm][0] += 1
    c.close()
    return H, D, F, TE, TAcc


def pct(x): return round(100 * x[0] / x[1], 1) if x[1] else ""

os.makedirs(TAB, exist_ok=True)
with open(os.path.join(TAB, "tab11_taskspecific.csv"), "w") as fh:
    fh.write("model,arm,hallucination_pct,detection_success_pct,full_chain_pct,technique_exact_pct,tactic_accuracy_pct\n")
    for tag, db in (("32B", os.path.join(ROOT, "real.db")), ("7B", os.path.join(ROOT, "paper/data/real_7b.db"))):
        H, D, F, TE, TA = compute(db)
        for a in ("A1", "A2", "A3", "A4"):
            fh.write(f"{tag},{a},{pct(H[a])},{pct(D[a])},{pct(F[a])},{pct(TE[a])},{pct(TA[a])}\n")
print("wrote paper/tables/tab11_taskspecific.csv")
os.system(f"column -s, -t {os.path.join(TAB,'tab11_taskspecific.csv')}")
