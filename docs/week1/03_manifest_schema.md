# Ground-Truth Manifest Schema — CloudKC-Bench

**Owner:** Atishay | 🔒 **FREEZE-FIRST** · ⚠️ **Anna's Week-2 collectors/simulator depend on this**
**Canonical contract:** [manifest.schema.json](manifest.schema.json) (JSON Schema, draft 2020-12)

> **v3 (journal) — changed from v2:** added an optional `authorship` object (`author`, `reviewer`,
> `review_date`, `authored_before_system_final`) to record the **inter-rater check** and **held-out
> authorship-separation** provenance required at journal tier (v3 §4.3). All else unchanged; the
> `scenario_id` pattern already covers ~70 scenarios.

> **Why this document exists (plain language).** The manifest is the **answer key** for a scenario — the
> machine-readable truth of what the attack actually did: which stages, in what order, mapped to which ATT&CK
> techniques, evidenced by which log events, at what times. Everything downstream depends on it: the
> simulator *emits* it, and the matching function (`04`) *scores against* it. Because it is a contract
> between two people's code, it is frozen first and changed only by agreement.

---

## 1. Manifest vs Finding — two different objects (do not confuse)

| | **Finding** (`models.py`, `docs/schemas.md`) | **Manifest** (this doc) |
|---|---|---|
| What it is | A detection a *running detector* emits | The *ground-truth answer key* for a scenario |
| Produced by | Collectors / hunters / arms at runtime | The `attack_simulator` when it scripts the attack |
| Used for | The system's output | Scoring the system's output |
| Contains truth? | No — it's a *claim* | **Yes — it is the truth** |

The manifest is **only ever used for scoring** and is **never given to the arms** (spec §6).

## 2. Top-level fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `scenario_id` | string | yes | Unique ID, e.g. `KC-02`. Pattern: `(SD\|KC\|LS\|EP\|BN\|HO)-\d{2}`. |
| `category` | enum | yes | One of `single_domain`, `multi_stage_kill_chain`, `low_and_slow`, `ephemeral`, `benign`. |
| `real_incident_reference` | string | yes | Locatable grounding source, or `"N/A - synthetic benign baseline"`. |
| `stages` | array | yes | Ordered list of stage objects (§3). **Empty `[]` for benign scenarios.** |
| `authorship` | object | no | `{author, reviewer, review_date, authored_before_system_final}` — inter-rater & held-out provenance (v3 §4.3). |
| `schema_version` | string | no | Manifest schema version, e.g. `"1.0"`. Recommended for forward-compat. |

## 3. Stage object fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `stage_id` | integer ≥ 1 | yes | 1-based position in the kill chain. Defines ground-truth order. |
| `ttp_id` | string | yes | ATT&CK ID, pattern `T\d{4}(\.\d{3})?`, e.g. `T1098.001`. |
| `ttp_name` | string | yes | Human-readable technique name (matches `tools/mitre_lookup.py` where present). |
| `telemetry_source` | enum | yes | One of `CloudTrail`, `VPC`, `S3`, `EC2`. The source the evidence lives in. |
| `evidence_event_ids` | array[string] | yes | IDs of the log events that constitute this stage (≥ 1). Bound in Week 2. |
| `timestamp_range` | array[string] (len 2) | yes | `[start, end]`. Relative (`"T+0s"`) in Week 1; absolute ISO-8601 once logs exist. |

## 4. Semantic decisions (frozen here; consumed by `04`)

1. **Order sensitivity — ORDER MATTERS for full credit.** `stage_id` defines the canonical order. A chain
   detected out of order is *partially* correct: the matching function awards per-stage credit for correctly
   identified stages but applies an order penalty (defined in `04`). This is the consistent contract both
   documents share — **`03` and `04` must agree on this.**
2. **Partial credit is allowed.** Catching stages 1–3 of a 5-stage chain scores higher than catching none.
   Scoring is per-stage, never all-or-nothing.
3. **Stage-to-event binding is authoritative.** A detected stage only earns credit if the events it cites
   actually appear in that stage's `evidence_event_ids` (prevents "right answer, wrong reason"). The matching
   function (`04`) enforces this against the manifest.
4. **Benign convention:** `category: "benign"` ⇒ `stages: []`. Any stage a system reports on a benign
   scenario is a false positive.
5. **Evidence IDs are placeholders in Week 1.** They become real once the simulator + collectors run
   (Week 2). The *structure* is frozen now; the *values* are bound later.

## 5. Validation

`manifest.schema.json` is the canonical machine-checkable contract. Every manifest the simulator emits — and
every worked example in `02_scenario_taxonomy.md` — must validate against it:

```bash
python -m jsonschema -i <some_manifest.json> docs/week1/manifest.schema.json
# or: check-jsonschema --schemafile docs/week1/manifest.schema.json <some_manifest.json>
```

## 6. Canonical example

See `02_scenario_taxonomy.md` §5 for worked `SD-01`, `KC-02`, and `BN-01` manifests. The `KC-02` example is
the reference for a complete multi-stage manifest.
