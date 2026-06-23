# P1 Sync Checkpoint — Agenda & Decision Log

**Owner:** shared (Atishay + Anna) | **Attendee:** Dr. S. Nagasundari
**When:** End of P1
**Status:** DRAFT agenda

> **v3 (journal) — changed from v2:** added the three journal-tier supervisor decisions that block P2 (venue,
> real-AWS budget, LLMCloudHunter scope — v3 §14), plus journal-scope sign-off. These are the items only the
> supervisor can resolve; the rest of P1 proceeds on the LocalStack-first path regardless.

> **Why this meeting exists (plain language).** Week 1 is the design freeze. Before anyone writes Week-2
> code, the supervisor confirms the scope and framing, and the team records the answers to a few decisions
> that have been deliberately left open in the freeze documents. Recording these in the decision log below
> makes them part of the frozen design.

---

## Agenda

1. **Confirm framing: benchmark + study, not just a system.** The contribution is CloudKC-Bench (dataset +
   manifests + matching function) and the four-arm ablation study — not "we built CloudSentinel." Confirm
   this is the agreed scope.

2. **Confirm GuardDuty is an explicit STRETCH / optional goal.** GuardDuty does not run on LocalStack, so any
   GuardDuty comparison is real-AWS only, secondary, and caveated — dropped entirely if Week 3 slips. Confirm.

3. **Confirm held-out sealing plan.** Held-out scenarios (`HO-01`…`HO-06` in `02_scenario_taxonomy.md`) are
   authored now and **moved to a sealed directory in Week 2**, untouched until P4. Confirm the mechanism
   (separate directory, commit-locked) and who owns sealing.

4. **RESOLVE: multi-stage scenario count (6 vs 8).** The implementation plan says Atishay authors **6**
   multi-stage scenarios (→ 22 dev total); the study guide §4.2 says **8** (→ 24 dev total). The catalog
   currently defaults to **8 / 24**. Pick one.

5. **Co-sign the pre-registration thresholds (`01_pre_registration.md` §3).**
   - H1 margin (default proposed: **≥ 0.15 absolute recall**, multi-stage category).
   - H2 equivalence band (default proposed: **|F1 diff| < 0.05**).
   - Pinned model version + date, compute budget, seed list (fill the held-fixed config, `01` §6).

6. **Confirm matching-function open decisions (`04` §7).**
   - Exact-TTP-only vs parent-technique credit.
   - Exact `order_penalty` form.
   - Evidence-binding threshold (≥1 overlap vs stricter).

7. **Confirm the v2 design supersedes the existing scaffolding.** The pre-v2 code in the repo (`collectors/`,
   `tools/`, `config.py`, …) is kept as Week-2/3 scaffolding; these freeze docs are now authoritative; no new
   infra code until the pre-registration is signed.

### Journal-tier (v3) decisions — BLOCK P2 (v3 §14)

8. **Journal venue (§14.1).** IEEE TIFS vs Computers & Security vs IEEE Access vs other — the bar and required
   scope differ. Pick the target so we size effort correctly.

9. **Real-AWS budget (§14.2) — BLOCKING.** Approve the estimated spend in `10_real_aws_setup.md` (~70
   scenarios × 4 arms × seeds, + GuardDuty). Confirm who owns the account and the spend cap. Until approved we
   stay LocalStack-first; real-AWS is the gated milestone.

10. **LLMCloudHunter reimplementation scope (§14.3).** Faithful **partial** reimplementation (acceptable in
    benchmark papers, documented deviations) vs **full** reimplementation — materially changes the P3 timeline.

11. **Journal-scope sign-off.** Confirm the move from workshop (v2) to journal (v3): ~70 scenarios, real-AWS
    primary, 3 external baselines, power analysis, failure-mode analysis, 25–30-paper review.

---

## Decision log (fill during/after the meeting)

| # | Decision | Outcome | Owner | Date |
|---|----------|---------|-------|------|
| 1 | Benchmark+study framing | | | |
| 2 | GuardDuty = stretch only | | | |
| 3 | Held-out sealing mechanism | | | |
| 4 | Multi-stage count (6 vs 8) | | | |
| 5a | H1 margin | | | |
| 5b | H2 equivalence band | | | |
| 5c | Pinned model + budget + seeds | | | |
| 6 | Matching-function decisions | | | |
| 7 | v2 supersedes scaffolding | | | |
| 8 | Journal venue | | | |
| 9 | Real-AWS budget approval | | | |
| 10 | LLMCloudHunter scope (partial/full) | | | |
| 11 | Journal-scope sign-off (v3) | | | |

## Week-1 Definition of Done — final check

- [ ] Pre-registration signed + dated (`01`)
- [ ] Manifest schema merged (`03` + `manifest.schema.json`)
- [ ] Matching-function spec merged (`04`)
- [ ] 24 dev + held-out scenarios authored; held-out marked for Week-2 sealing (`02`)
- [ ] This sync held; decisions logged above
