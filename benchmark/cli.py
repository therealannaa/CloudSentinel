"""CloudKC-Bench CLI — the P2 entry points.

Examples:
    python -m benchmark.cli generate --set dev
    python -m benchmark.cli generate --set all && python -m benchmark.cli seal-heldout
    python -m benchmark.cli summary
    python -m benchmark.cli clock --set dev
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

from benchmark import runner, heldout, clock_model, state_cache, matching, experiment, analysis
from benchmark.manifest import Manifest
from benchmark.simulator.specs import SCENARIO_SPECS, dev_ids, heldout_ids
from benchmark.simulator.builder import build_scenario
from benchmark.arms import ARMS


def cmd_generate(args):
    res = runner.generate(scenario_set=args.set, db_path=args.db,
                          manifests_dir=args.manifests, environment=args.environment)
    n_ev = sum(r["events"] for r in res.values())
    n_gt = sum(r["ground_truth"] for r in res.values())
    print(f"Generated {len(res)} scenarios (set={args.set}, env={args.environment}): "
          f"{n_ev} events ({n_gt} ground-truth). Manifests -> {args.manifests}/")
    print("All manifests validated against manifest.schema.json.")
    return 0


def cmd_summary(args):
    rows = runner.summary_table(db_path=args.db)
    print(f"{'category':<24}{'scenarios':>10}{'events':>9}{'ground_truth':>14}")
    for r in rows:
        print(f"{r['category']:<24}{r['n_scenarios']:>10}{r['n_events']:>9}{r['n_ground_truth'] or 0:>14}")
    return 0


def cmd_seal_heldout(args):
    lock = heldout.seal(heldout_dir=args.heldout_dir)
    print(f"Sealed {lock['n_manifests']} held-out manifests at {lock['sealed_at']}.")
    ok, mism = heldout.verify(heldout_dir=args.heldout_dir)
    print("Integrity:", "OK" if ok else f"FAIL {mism}")
    return 0 if ok else 1


def cmd_clock(args):
    ids = list(SCENARIO_SPECS) if args.set == "all" else \
        [s for s in SCENARIO_SPECS if not SCENARIO_SPECS[s]["held_out"]]
    pairs = []
    for sid in ids:
        events, _ = build_scenario(sid, SCENARIO_SPECS[sid])
        pairs.extend(clock_model.synthetic_pairs(events))
    stats = clock_model.summarize(pairs)
    print(json.dumps(stats, indent=2))
    return 0


def cmd_selfcheck(args):
    """Run the entire P2 pipeline in a throwaway workspace and report PASS/FAIL:
    generate all -> validate -> ingest -> seal+verify held-out -> score -> clock."""
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "selfcheck.db")
        manifests = os.path.join(tmp, "manifests")

        print("1. generate + validate + ingest (all 69 scenarios)")
        res = runner.generate("all", db_path=db, manifests_dir=manifests)
        check("69 scenarios generated", len(res) == 69)
        check("every manifest written", all(os.path.exists(r["manifest"]) for r in res.values()))

        conn = state_cache.connect(db)
        rows = {r["category"]: r for r in state_cache.scenario_summary(conn)}
        total_events = state_cache.event_count(conn)
        conn.close()
        check("events ingested", total_events > 0)
        check("benign has no ground-truth events", (rows["benign"]["n_ground_truth"] or 0) == 0)

        print("2. seal + verify held-out")
        heldout_dir = os.path.join(manifests, "heldout")
        lock = heldout.seal(heldout_dir)
        ok, mism = heldout.verify(heldout_dir)
        check("10 held-out manifests sealed", lock["n_manifests"] == 10)
        check("held-out integrity OK", ok and not mism)

        print("3. score reconstructed chains (matching function)")
        _, m = build_scenario("KC-02", SCENARIO_SPECS["KC-02"])
        md = m.to_dict()
        perfect = matching.score({"stages": md["stages"]}, md)
        empty = matching.score({"stages": []}, md)
        check("perfect reconstruction -> recall=1.0", perfect.recall == 1.0)
        check("empty reconstruction -> recall=0.0", empty.recall == 0.0)
        bn = build_scenario("BN-01", SCENARIO_SPECS["BN-01"])[1].to_dict()
        benign = matching.score({"stages": []}, bn)
        check("benign no-report -> precision=1.0", benign.precision == 1.0)

        print("4. clock model")
        pairs = []
        for sid in dev_ids()[:10]:
            evs, _ = build_scenario(sid, SCENARIO_SPECS[sid])
            pairs.extend(clock_model.synthetic_pairs(evs))
        stats = clock_model.summarize(pairs)
        check("clock skew CloudTrail>EC2",
              stats["per_source"]["CloudTrail"]["median"] > stats["per_source"]["EC2"]["median"])

    passed = sum(1 for _, c in checks if c)
    print(f"\nSELF-CHECK: {passed}/{len(checks)} passed -> "
          f"{'PASS' if passed == len(checks) else 'FAIL'}")
    return 0 if passed == len(checks) else 1


def cmd_run_arms(args):
    from benchmark.arms.llm_client import LLMError
    arms = [a.strip().upper() for a in args.arms.split(",")]
    scope = f"set={args.set}" + (f", limit={args.limit}" if args.limit else "")
    print(f"Running arms {arms} on {scope}, seeds={args.seeds}, env={args.environment} ...")
    try:
        results = experiment.run_experiment(
            arms=arms, scenario_set=args.set, seeds=args.seeds, db_path=args.db,
            manifests_dir=args.manifests, environment=args.environment, limit=args.limit)
    except LLMError as e:
        print(f"\nLLM backend error — aborted before writing misleading scores:\n{e}")
        return 2
    rows = analysis.per_category(results)
    print(f"\n{len(results)} runs scored. Per-(arm, category) means "
          "(seeds averaged to scenario, never pooled across categories):\n")
    analysis.print_table(rows)
    if args.csv:
        analysis.to_csv(rows, args.csv)
        print(f"\nWrote per-category results -> {args.csv}")
    # honest note on which backend produced these
    from benchmark.arms.llm_client import get_client
    backend = get_client().name
    print(f"\nLLM backend: {backend}"
          + ("" if backend == "gemini" else
             "  (deterministic offline backend — set GEMINI_API_KEY for real LLM arms; "
             "comparative H1/H2 numbers are only meaningful with a real LLM + real telemetry)"))
    return 0


def cmd_analyze(args):
    from benchmark import stats
    report = stats.full_report(db_path=args.db, environment=args.environment,
                              h1_margin=args.h1_margin, h2_band=args.h2_band)
    stats.print_report(report)
    if args.csv and not report.get("error"):
        stats.to_csv(report["per_category_recall"], args.csv)
        print(f"\nWrote per-category recall (with CIs) -> {args.csv}")
    return 1 if report.get("error") else 0


def cmd_localstack_check(args):
    from benchmark.simulator import localstack_backend as lsb
    try:
        clients = lsb.make_clients()
    except lsb.LocalStackUnavailable as e:
        print(f"localstack: UNAVAILABLE — {e}")
        return 1
    ok = lsb.check_connectivity(clients)
    print(f"localstack at {lsb.LOCALSTACK_URL}: {'REACHABLE' if ok else 'NOT REACHABLE (run docker compose up -d)'}")
    return 0 if ok else 1


def build_parser():
    p = argparse.ArgumentParser(prog="benchmark", description="CloudKC-Bench P2 generator")
    p.add_argument("--db", default="cloudsentinel.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="generate a scenario set + manifests + events")
    g.add_argument("--set", choices=["dev", "heldout", "all"], default="dev")
    g.add_argument("--manifests", default="benchmark/manifests")
    g.add_argument("--environment", default="synthetic",
                   choices=["synthetic", "localstack", "real_aws"])
    g.set_defaults(func=cmd_generate)

    s = sub.add_parser("summary", help="per-category scenario/event counts")
    s.set_defaults(func=cmd_summary)

    h = sub.add_parser("seal-heldout", help="seal the held-out manifests")
    h.add_argument("--heldout-dir", default="benchmark/manifests/heldout")
    h.set_defaults(func=cmd_seal_heldout)

    c = sub.add_parser("clock", help="report synthetic clock-model stats")
    c.add_argument("--set", choices=["dev", "all"], default="dev")
    c.set_defaults(func=cmd_clock)

    sc = sub.add_parser("selfcheck", help="run the whole P2 pipeline and report PASS/FAIL")
    sc.set_defaults(func=cmd_selfcheck)

    lc = sub.add_parser("localstack-check", help="check LocalStack reachability (needs boto3 + compose up)")
    lc.set_defaults(func=cmd_localstack_check)

    an = sub.add_parser("analyze", help="P4 stats: H1/H2 verdicts + bootstrap CIs from a past run")
    an.add_argument("--environment", default=None,
                    help="filter to runs from this environment (synthetic|localstack|real_aws)")
    an.add_argument("--h1-margin", type=float, default=0.15, dest="h1_margin")
    an.add_argument("--h2-band", type=float, default=0.05, dest="h2_band")
    an.add_argument("--csv", default=None)
    an.set_defaults(func=cmd_analyze)

    ra = sub.add_parser("run-arms", help="run the A1-A4 ablation and score it")
    ra.add_argument("--arms", default=",".join(ARMS))
    ra.add_argument("--set", choices=["dev", "heldout", "all"], default="dev")
    ra.add_argument("--seeds", type=int, default=3)
    ra.add_argument("--manifests", default="benchmark/manifests")
    ra.add_argument("--environment", default="synthetic",
                    choices=["synthetic", "localstack", "real_aws"])
    ra.add_argument("--limit", type=int, default=None,
                    help="run only the first N scenarios (cheap smoke test for paid LLM runs)")
    ra.add_argument("--csv", default=None)
    ra.set_defaults(func=cmd_run_arms)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
