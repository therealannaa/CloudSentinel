# Week 1 — Phase P1: Freeze Design

**Project:** CloudKC-Bench — LLM Cross-Domain Correlation for AWS Kill-Chain Reconstruction
**Team:** Atishay & Anna | ISFCR, PES University | **Supervisor:** Dr. S. Nagasundari
**Week 1 window:** June 16–22, 2026

---

## What Phase P1 is (and why there is no code)

This project's primary deliverable is a **research benchmark for an IEEE CLOUD 2026 paper**, not just a
working system. The most common reason security-ML papers get rejected is that the authors made measurement
decisions *after* seeing results (confirmation bias, p-hacking, pseudo-replication). Week 1 prevents that by
**writing down and freezing — in advance — every decision that could later be massaged**: the hypotheses, the
pass/fail thresholds, the scenario set, the ground-truth format, and the scoring algorithm.

> **The Week-1 rule (from the implementation plan):** *Neither person writes a line of infrastructure code
> until this is done.* Week 1 produces **documents and schemas**, not running code.

There *is* already code in this repo (`collectors/`, `tools/`, `config.py`, `docker-compose.yml`, …). That
was written under the pre-v2 understanding of the project. Under the v2 redesign it counts as **early
Week-2/3 scaffolding**, not Week-1 work — it is kept and reused later, not rolled back. These Week-1 freeze
documents become the **authoritative spec that the scaffolding must conform to** in Weeks 2–4.

---

## The 8 deliverables

| # | File | Owner | Freeze status |
|---|------|-------|---------------|
| 0 | [00_README.md](00_README.md) (this file) | shared | — |
| 1 | [01_pre_registration.md](01_pre_registration.md) — RQ, H1, H2, thresholds, frozen protocol | **Atishay** (Anna co-signs) | 🔒 |
| 2 | [02_scenario_taxonomy.md](02_scenario_taxonomy.md) — 24 dev + held-out scenario catalog | **Atishay** (SD+KC) / Anna (LS, EP, BN, HO) | — |
| 3 | [03_manifest_schema.md](03_manifest_schema.md) + [manifest.schema.json](manifest.schema.json) | **Atishay** | 🔒 ⚠️ |
| 4 | [04_matching_function_spec.md](04_matching_function_spec.md) | **Anna** | 🔒 ⚠️ |
| 5 | [05_sqlite_state_cache_schema.md](05_sqlite_state_cache_schema.md) | **Atishay** | — |
| 6 | [06_clock_model.md](06_clock_model.md) — template now, measured Week 2 | **Anna** | — |
| 7 | [07_sync_checkpoint_agenda.md](07_sync_checkpoint_agenda.md) | shared | — |

**Legend:** 🔒 = *freeze-first* (must be locked in writing before dependent work begins). ⚠️ = *blocking
dependency* for the other person (Anna's Week-2 collectors depend on #3; Atishay's Week-3 arms depend on #4).

---

## Week-1 Definition of Done (from the implementation plan)

- [ ] **Pre-registration** document signed, dated, and saved to the repo (`01_pre_registration.md`).
- [ ] **Manifest schema** merged (`03_manifest_schema.md` + `manifest.schema.json`).
- [ ] **Matching-function spec** merged (`04_matching_function_spec.md`).
- [ ] **24 dev scenarios + held-out set authored**; held-out set marked to be sealed in Week 2
      (`02_scenario_taxonomy.md`).
- [ ] **Sync checkpoint** held with Dr. Nagasundari; decisions logged (`07_sync_checkpoint_agenda.md`).

When all five boxes are checked, P1 is complete and Phase P2 (environment + benchmark generator) may begin.

---

## How these documents relate to the existing repo

- **`docs/schemas.md`** documents the v1 runtime **`Finding`** schema (what a *detector* emits at runtime).
  The new **manifest** schema (#3) is the **ground-truth answer key** (what the attack *actually did*). These
  are two different objects; both are kept. See #3 for the explicit distinction.
- **`config.py`** already defines thresholds (`EXFIL_THRESHOLD_MB`, `PORT_SCAN_THRESHOLD`,
  `MASS_DOWNLOAD_THRESHOLD`, `EPHEMERAL_INSTANCE_THRESHOLD`, approved regions). Week-1 docs reference these
  rather than redefining them.
- **`tools/mitre_lookup.py`** curates 19 ATT&CK-for-Cloud techniques; the scenario taxonomy (#2) grounds its
  TTP IDs in that set wherever possible.

## Glossary

For definitions of every term used here (kill chain, TTP, ablation, bootstrap CI, pseudo-replication, …) see
the project **study guide** (`cloudsentinel_study_guide.md`), "Quick Reference: Key Terms".
