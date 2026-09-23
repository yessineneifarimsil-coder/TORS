# Submission Package

## Manuscript

**Title (final, applied consistently to the manuscript, running head and PDF):**

> Context-Dependent Selection of Established Urban Routing Policies:
> Regime Effects, Decision Value, and Generalization Limits

Running head: *Context-Dependent Selection of Urban Routing Policies*.
Authors and institution are anonymised, matching the repository's prior
IC_TORS'26 submission.

**Version:** final submission version. `../CHANGELOG.md` lists every change
from the completed study, each traceable to an existing artefact.

## Evidence behind the manuscript

| Count | Value |
|---|---|
| **Valid main-campaign runs** | **12,960** = 648 contexts x 4 policies x 5 paired seeds |
| Total simulations attempted | 20,284 |
| Total succeeded | 18,124 (384 scenario-validation, 640 screening, 12,960 main, 1,920 sensitivity, 1,080 domain-shift, 1,140 boundary-refinement) |
| Failed | 2,160, the infeasible bypass-incident split (Section 6 of the paper) |

Zero failed runs and zero teleports in the main campaign; minimum completion
rate 1.0000. **Every result in the paper derives from the 12,960 unless the text
says otherwise.** The two totals are not interchangeable.

## Files

| File | Contents |
|---|---|
| `main.tex` | manuscript root (llncs) |
| `lncs_front.tex` | document class and packages |
| `abstract.tex`, `sec1`--`sec9_*.tex` | body sections |
| `numbers.tex` | **generated** — every numeric claim in the paper |
| `tables/tab1`--`tab7_*.tex` | **generated** tables |
| `figures/fig*.pdf` | figures, generated at LNCS text width |
| `references.bib` | 23 references, all cited, all verified |
| `main.pdf` | compiled manuscript |
| `check_macros.py` | build-time check that the text cites no number the analysis did not produce |

## Compiling

```bash
pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Requires the `llncs` class and `splncs04.bst` (TeX Live `texlive-publishers`).

To regenerate the numbers, tables and figures from the run records first:

```bash
cd ..                            # study/
python3 analysis/run_analysis.py # -> results/results.json
python3 analysis/augment.py
python3 analysis/sensitivity.py
python3 analysis/emit_numbers.py # -> paper/numbers.tex
python3 analysis/tables.py       # -> paper/tables/
python3 figures/fig1_network.py && python3 figures/fig3_design.py
python3 figures/figs_results.py
cp figures/fig*.pdf paper/figures/
```

## Verification

```bash
python3 paper/check_macros.py        # every \Num macro resolves
python3 audit/qc_gate.py             # 17 scientific quality-control checks
python3 audit/submission_audit.py    # 17 submission checks (questions A-P)
```

All three pass on the committed state.

## UNRESOLVED SUBMISSION DEPENDENCY

**No official IC_TORS'26 / TORS'26 author template, class file, formatting
instruction or page limit was found** in the repository, the archives or the
uploaded material. Nothing about the conference's requirements has been invented
here. Two facts were used instead, both verifiable in the repository:

1. The repository's own prior IC_TORS'26 submission
   (`paper/IC_TORS26_SHAP_MCDM_conference_final_2026-08-27_v11.tex`) uses
   `\documentclass[runningheads]{llncs}` with anonymised author and institution.
   This manuscript matches that class and that convention.
2. That prior submission compiles to **12 pages**. This manuscript compiles to
   **25 pages**.

**Action required before submission.** Confirm the official template and page
limit. If a limit of 12–15 pages applies, this manuscript must be condensed;
it has not been pre-emptively compressed, because compressing to an invented
limit would have degraded readability for no verified reason. Condensation
should be taken in this order, which removes presentation before evidence:

1. Move Tables 6 and 7 and Figures 3 and 6 to supplementary material (~4 pages).
2. Reduce the Experimental Integrity section to a half-page summary with the
   detail in supplementary material (~1 page) — but retain the disclosure of
   deviation D-1 and the infeasible split in the main text.
3. Condense Results 5.5 (noise and resolution) and 5.9 (boundary refinement)
   into one subsection (~1.5 pages).
4. Shorten Related Work to two subsections (~1 page).

Steps 1–4 reach roughly 17 pages without removing a result. Going below that
requires cutting evidence, and which evidence to cut is a decision for the
authors.
