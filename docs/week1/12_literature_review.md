# Literature Review — Structure & Seed (25–30 papers)

**Owner:** Anna | **Status:** SKELETON — seeded with verified citations; expand to 25–30 papers.

> **Why this document exists (plain language).** A workshop paper can list 5–6 references; a journal expects a
> *structured, taxonomic* review of 25–30 papers that maps the whole research space and ends each theme with
> "what this body of work leaves open, and how we address it." This skeleton fixes the structure and seeds it
> with the citations already verified to locatable sources, so nobody re-introduces an unverifiable reference.

---

## Coverage areas & minimum counts (v3 §8.1)

| Area | Min papers | Seed citations (verified) |
|------|------------|---------------------------|
| LLM-for-security detection | 6–8 | LLMCloudHunter (arXiv:2407.05194); HuntGPT — Ali & Kostakos 2023 (arXiv:2309.16021); + LLM log-analysis, LLMSAN |
| Cloud security detection | 5–6 | GuardDuty architecture; AWS-native multi-agent security (Bedrock); CSPM/Stratus (github.com/DataDog/stratus-red-team) |
| Multi-agent systems for security | 3–4 | Mukherjee & Kantarcioglu 2025 (provenance/agentic hunting); CAMEL-for-security; agentic hunting survey (arXiv:2510.06445) |
| Security benchmarks & evaluation | 5–6 | CyberSOCEval (arXiv:2509.20166); ExCyTIn-Bench (arXiv:2507.14201); OrgForge-IT (arXiv:2603.22499); ACSE-Eval (arXiv:2505.11565); SecBench |
| Kill-chain & ATT&CK modelling | 3–4 | MITRE ATT&CK for Cloud (IaaS); kill-chain formalisms; provenance graphs (DARPA TC/OpTC) |
| RAG / knowledge retrieval for security | 2–3 | security RAG systems; threat-intel retrieval |

## Section structure for the paper (v3 §8.2) — NOT a sequential list

Each subsection ends with a crisp "**leaves open → we address**" paragraph.

1. **LLM-Assisted Security Detection: capabilities and limits.**
   *Leaves open → we address:* `<stub — e.g. prior LLM-security work targets rule generation or single-host
   IDS, not multi-stage AWS control-plane kill-chain reconstruction with mechanical scoring.>`
2. **Cloud-Native Threat Detection: AWS-specific prior work.**
   *Leaves open → we address:* `<stub>`
3. **Multi-Agent Architectures for Security Tasks.**
   *Leaves open → we address:* `<stub — multi-agent value is asserted, rarely ablated; our H2 tests it.>`
4. **Security Benchmarks: design, coverage, and gaps.** ← hosts the **coverage-gap table** (`09`).
   *Leaves open → we address:* `<stub — existing benchmarks are Azure/QA/malware/CTI, not AWS-control-plane
   kill chains with ground-truth manifests.>`
5. **Kill-Chain Reconstruction and ATT&CK Modelling.**
   *Leaves open → we address:* `<stub>`

## Citation hygiene rule

Every reference must trace to a locatable source (arXiv ID, DOI, or official repo/page) — mirror the
spec's Source-Verification Ledger. All coverage-gap competitors are now located: OrgForge-IT
(arXiv:2603.22499, insider-threat benchmark), ACSE-Eval (arXiv:2505.11565, AWS threat-modeling of IaC).
See `09_coverage_gap_table.md` for the per-paper property assessment.
