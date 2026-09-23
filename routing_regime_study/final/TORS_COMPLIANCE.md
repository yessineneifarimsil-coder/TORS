# IC_TORS'26 Submission Compliance

Status of this manuscript against IC_TORS'26 requirements, separating what was
**verified**, what is **precedent taken from this project**, and what remains
**unverified**. Nothing about the conference is asserted here that was not obtained
from a source named below. No page limit, margin, font, class name or submission
requirement is invented.

---

## 1. Package contents

| File | Role |
|---|---|
| `main.tex` | The complete manuscript. Standalone: no `\input`, no `\include`, all tables inline. |
| `references.bib` | 30 entries, all cited, all resolving. |
| `figures/` | Five figure PDFs, referenced by `main.tex` as `figures/<name>.pdf`. |
| `TORS_COMPLIANCE.md` | This file. Not part of the submission itself. |

Nothing else is included. No auxiliary `.tex` sections, no `.aux`/`.log`/`.bbl`/`.blg`/`.out`,
no compiled PDF, no scripts, no data.

## 2. Compilation

Tested from a clean extraction of this package into an empty directory:

```
pdflatex main
bibtex   main
pdflatex main
pdflatex main
```

Result: **0 errors, 0 undefined citations, 0 undefined references, 0 missing figures,
0 overfull boxes, 22 pages.** On Overleaf, select pdfLaTeX; the standard
"pdfLaTeX + BibTeX" recipe runs exactly the sequence above.

Required by the class file used: `llncs.cls` and `splncs04.bst`, both part of the
standard TeX Live distribution and present on Overleaf. The preamble also uses
`lmodern`, `microtype`, `amsmath`, `amssymb`, `graphicx`, `booktabs`, `tabularx`,
`array`, `hyperref` and `url` — all standard.

---

## 3. Conference identification — VERIFIED FROM SECONDARY SOURCES ONLY

| Item | Value |
|---|---|
| Conference | IC_TORS'26 — 8th International Conference of the Tunisian Operational Research Society |
| Dates | 20–22 December 2026 |
| Location | Sousse, Tunisia |
| Publication partner | organised in collaboration with **Springer** |
| Official site | `www.ic-tors26.tn` (also `ic-tors26.tilda.ws`) |
| Paper submission deadline | extended to **12 September 2026** |

> **The official conference website could not be retrieved.** `ic-tors26.tilda.ws`,
> `www.ic-tors26.tn`, the IFORS listing and the INFORMS Open Forum thread are all
> blocked by this environment's network egress policy. Every row above comes from
> search-result summaries of those pages, not from the pages themselves.
> **Confirm each row against the official site before submitting.**

> **Deadline warning.** The recorded deadline (12 September 2026) precedes the date
> this manuscript was prepared. Confirm whether a further extension applies.

---

## 4. Format — NOT VERIFIED; chosen from this project's own precedent

**No official IC_TORS'26 author template, class file, style file or formatting
instruction exists in this repository or in the supplied material.** A
filesystem-wide search for `*.cls` and `*.sty` returned none for this conference.

The format was therefore chosen from the one piece of verifiable evidence available:
a **prior IC_TORS'26 submission present in this repository**,
`paper/IC_TORS26_SHAP_MCDM_conference_final_2026-08-27_v11.tex`, which uses
`\documentclass[runningheads]{llncs}` with an anonymous author block. This manuscript
matches that class and that convention.

The Springer collaboration noted in section 3 is **consistent** with an LNCS-family
template but does **not** confirm it: Springer publishes several series (LNCS, LNBIP,
CCIS, AISC) with different templates.

**If the official template differs,** the manuscript body transfers unchanged; only
the preamble and the bibliography style need substitution.

---

## 5. Page count — target 16–20, delivered 22

**No page limit for IC_TORS'26 was found, and none is invented here.**

| | |
|---|---|
| This manuscript | **22 pages** in `llncs` (the last page is ~35 % full, so ~21.3 pages of content) |
| Editorial target set for this revision | 16–20 pages |
| Prior IC_TORS'26 submission in this repository | 12 pages in the same class |

The manuscript exceeds the 16–20 editorial target by about two pages. Every page
other than the last is fully set — the length is content, not whitespace: five
figures, six tables, thirty references and a results section that reports the regime
map, the decision ladder, the noise analysis, the mechanism decomposition, the
multi-criteria analysis, the robustness battery and the extrapolation failure.

If a hard limit turns out to apply, condense in this order. Each step is
self-contained and removes no result:

1. **Move the mechanism decomposition (Table 4 and Section 6.6) to an appendix or
   supplement** — it explains the reversal but no conclusion depends on it. ≈1 page.
2. **Merge Figure 2 into Figure 3** as a two-panel figure, keeping journey time and
   CO₂ and dropping the stopped-time panel (its content is in Figure 5b). ≈0.4 page.
3. **Compress Section 2** by removing the per-strand "what is measured here" sentences
   and keeping only the closing positioning paragraph. ≈0.5 page.
4. **Drop the four multi-criteria method references** (`hwang1981multiple`,
   `opricovic2004compromise`, `brans1985preference`, `ehrgott2005multicriteria`) and
   the sentence that cites them; the paper uses none of those methods. ≈0.3 page.

Steps 1–4 reach approximately 20 pages. Do not apply step 3 if the three-subsection
Literature Review structure must be preserved verbatim — it thins but does not remove
the subsections.

---

## 6. Anonymity — NOT VERIFIED

Whether IC_TORS'26 uses double-blind review could not be confirmed. The manuscript is
**anonymous**, matching the prior submission in this repository. The author block is:

```latex
\author{Anonymous author(s)}
\authorrunning{Anonymous submission}
\institute{Affiliations withheld for review}
```

If review is not blind, replace those three lines with the real names, running
authors and affiliations. Nothing else in the manuscript identifies the authors:
there is no acknowledgements section, no funding statement and no self-citation.

---

## 7. Numerical provenance

Every numerical claim in the manuscript derives from one file, the run-level table of
the 432 completed simulations (`analysis/runs.csv` in the study repository, built from
the `RAW_PERFORMANCE` sheet of the audited workbook). Two automated checks are kept in
the repository and were run against the delivered `main.tex`:

- `analysis2/verify.py` recomputes **77** previously published quantities from
  `runs.csv` and compares them to the recorded results. All 77 match exactly.
- `analysis2/audit_manuscript.py` checks that **102** load-bearing numeric strings in
  `main.tex` are present and equal to the recomputed values. All 102 match.

**One correction was made** relative to earlier drafts of this study. The
measurement-boundary check — recomputing every decision on in-network journey time
instead of full journey time — was previously reported as changing the headroom from
0.03018 to **0.03281**. That value does not reproduce from `runs.csv` under any of the
eight plausible normalisation conventions tested. The reproducible value, recomputing
the time reference on the in-network scale, is **0.03305**; the manuscript reports
that. The qualitative conclusion is unchanged: 0 of 24 preferred-policy labels change.

## 8. What was not done

- **The switching boundary is bracketed, not located.** Localising it would require
  144 additional runs at intermediate demand levels on this same network. Those runs
  were not executed, because the network and scenario configuration files for this
  benchmark are not present in the analysis environment and a reconstructed network
  would not be comparable with the 432 completed runs. This is stated in the
  manuscript (Sections 5.3 and 6.10), and no claim depends on it.
- **No result from any other network or experiment is used.** All numbers come from
  the 432-run campaign on the twelve-signal mesh.
- **No statistical significance is claimed anywhere.** The resolution criterion
  |d̄| > 2·SE(d̄) is declared in Section 5.5 as a descriptive threshold on three paired
  replications, explicitly not a hypothesis test.
- **79.9 % is a decision statistic**, the fraction of available decision headroom
  captured. The manuscript states in Section 6.4 that it is not a percentage reduction
  in travel time or emissions, and reports the physical differences (13.00 s and
  30.71 g per vehicle) separately.

---

## 9. Checklist

| Requirement | Status |
|---|---|
| Exact top-level structure (7 sections + references) | PASS |
| Exactly three Literature Review subsections | PASS |
| No separate Discussion / Limitations / Future Work section | PASS |
| Original 432-run study remains the core | PASS |
| No results imported from another network | PASS |
| No invented experiments, numbers or citations | PASS |
| All numerical claims trace to source data | PASS — 102/102 audited |
| 79.9 % described as headroom capture | PASS |
| Figures 1–4 necessary and readable | PASS |
| Optional Figure 5 justified (Pareto; no equivalent table) | PASS |
| References resolve | PASS — 30/30, 0 undefined |
| Figures resolve | PASS — 5/5, 0 missing |
| `main.tex` compiles independently | PASS — clean extraction tested |
| No `\input` / `\include` | PASS |
| Tables inline | PASS — 6/6 |
| Overfull boxes | PASS — 0 |
| PDF 16–20 pages | **NOT MET — 22 pages.** See section 5 for the condensation route. |
| Package contains only the requested files | PASS — 4 items |
