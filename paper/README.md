# Paper — CloudKC-Bench (IEEE journal draft)

LaTeX (IEEEtran) draft targeting **IEEE TIFS / Computers & Security**. `main.tex` +
`references.bib`.

## Compile

**Overleaf (easiest, no local setup):** create a project, upload `main.tex` and
`references.bib`, set the compiler to *pdfLaTeX*. IEEEtran is built in.

**Locally:**
```bash
cd paper
latexmk -pdf main.tex        # or: pdflatex main; bibtex main; pdflatex main; pdflatex main
```

## What's written vs. pending

The draft is a complete skeleton. Sections that **don't** depend on results are written
substantively now:
- Abstract (headline sentence is a placeholder), Introduction, Background
- **Related Work** — full taxonomy + the coverage-gap table (Table I), filled from the
  five competitor papers (see `../docs/week1/09_coverage_gap_table.md`)
- **CloudKC-Bench Design**, System Architecture, Experimental Setup (incl. the honest
  power-analysis framing), Threats to Validity

Placeholders are impossible to miss:
- `\result{...}` (red) — fill from the run: **Results** (H1/H2 verdicts, per-category
  table, cost/latency) and **Failure-Mode Analysis**.
- `\todo{...}` (blue) — small items (pinned model+date+seeds, archival DOI).

## How results flow into the paper

Once Anna's `run-arms` completes:
```bash
python -m benchmark.cli analyze   --csv paper/data/by_category.csv   # -> Table II + H1/H2 numbers
python -m benchmark.cli failures  --csv paper/data/miss_rates.csv    # -> Failure-Mode section
```
Copy the H1/H2 verdict lines into the `\result{...}` blocks in Section VII, the
per-category CIs into Table II, and the miss-rate breakdown into Section VIII.
(We can add a small script to emit LaTeX table rows directly from those CSVs.)

## Section ownership (per plan v3 §11)
- **Atishay:** Abstract, Background, CloudKC-Bench Design, System, Experimental Setup,
  Results, Failure-Mode Analysis.
- **Anna:** Introduction, Related Work, Discussion, Conclusion.
- **Shared:** Threats to Validity.

## Before submission
- Confirm the `$\circ$` (partial) cells in Table I against the full competitor papers.
- Fill the pinned model + date + seed list (Setup) and swap the repo URL for the DOI.
- Expand Related Work toward 25–30 references (`../docs/week1/12_literature_review.md`).
- Verify every `\cite` resolves; `capitalone2019` note flags a source to finalise.
