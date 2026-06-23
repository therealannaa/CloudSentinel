# Coverage Gap Table — C1 Novelty Defence

**Owner:** Anna | **Status:** DRAFT — competitor cells are ❓ until each paper is **read in full**.

> **Why this document exists (plain language).** Contribution C1 claims CloudKC-Bench is the *first* open
> benchmark targeting AWS control-plane multi-stage kill chains specifically. A reviewer connected to any
> competing project will check this claim cell by cell. This table is the evidence: six properties × six
> benchmarks. The "first" claim is only defensible once every ❓ is replaced with ✅ / ❌ / Partial **after
> reading the actual paper** — not the abstract.

---

## The table (v3 §4.4)

| Property | CyberSOCEval | ExCyTIn-Bench | OrgForge-IT | LLMCloudHunter | ACSE-Eval | **CloudKC-Bench (ours)** |
|---|---|---|---|---|---|---|
| AWS control-plane specific | ❓ | ❓ | ❓ | Partial | ❓ | ✅ |
| Multi-stage kill chains | ❓ | ❓ | ❓ | ❌ | ❓ | ✅ |
| Open + reproducible | ❓ | ❓ | ❓ | ❌ | ❓ | ✅ |
| Machine-checkable ground truth | ❓ | ❓ | ❓ | ❌ | ❓ | ✅ |
| ATT&CK-for-Cloud mapped | ❓ | ❓ | ❓ | Partial | ❓ | ✅ |
| Real-AWS validated | ❓ | ❓ | ❓ | ❌ | ❓ | ✅ (partial) |

## Per-paper reading checklist (fill the column, then delete ❓)

For each competitor, read the paper and answer the 6 properties with one-line evidence + a page/section cite:

- **CyberSOCEval** — arXiv:2509.20166; github.com/CrowdStrike/CyberSOCEval_data. *(Known: malware analysis +
  CTI reasoning QA — likely ❌ on multi-stage AWS kill chains; confirm.)*
- **ExCyTIn-Bench** — arXiv:2507.14201; github.com/microsoft/SecRL. *(Known: Azure, Sentinel tables, QA over
  investigation graphs — likely ❌ on AWS-control-plane + kill-chain reconstruction; confirm.)*
- **OrgForge-IT** — locate the paper/repo first (citation TBD); answer all 6.
- **LLMCloudHunter** — arXiv:2407.05194. *(Known: generates Sigma rules from CTI; not a benchmark, not
  reproducible kill-chain ground truth — Partial on AWS/ATT&CK, ❌ elsewhere; confirm.)*
- **ACSE-Eval** — locate the paper/repo first (citation TBD); answer all 6.

## The decision rule (non-negotiable)

- If **no** competitor satisfies all six properties → C1's "first … specifically" wording stands.
- If **any** competitor satisfies all six → **reword C1** from "first" to "**extends X by adding Y**"
  (name the closest competitor and the precise added property). Honesty here is what survives review.

> Cross-reference: the literature review (`12_literature_review.md`) §"Security Benchmarks" hosts the prose
> version of this comparison.
