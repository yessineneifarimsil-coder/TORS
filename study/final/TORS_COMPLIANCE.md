# IC_TORS'26 Submission Compliance

Status of this manuscript against IC_TORS'26 requirements, separating what was
**verified**, what is **prior-year precedent from this repository**, and what
remains **unverified**. Nothing about the conference is asserted here that was
not obtained from a source named below.

---

## 1. Conference identification — VERIFIED

| Item | Value | Source |
|---|---|---|
| Conference | IC_TORS'26 — 8th International Conference of the Tunisian Operational Research Society | public listings (IFORS, INFORMS Open Forum, EURO) |
| Dates | 20–22 December 2026 | same |
| Location | Sousse, Tunisia | INFORMS Open Forum CFP listing |
| Publication partner | organised in collaboration with **Springer** | conference announcement |
| Official site | `www.ic-tors26.tn` (also `ic-tors26.tilda.ws`) | search results |
| Paper submission deadline | extended to **12 September 2026** | conference announcement |

> **The official conference website could not be retrieved.** Both
> `ic-tors26.tilda.ws` and `www.ic-tors26.tn` are blocked by this environment's
> network egress policy, as is the IFORS listing and the INFORMS forum thread.
> Everything in the table above comes from search-result summaries of those
> pages, not from the pages themselves. **Confirm every row against the official
> site before submitting.**

> **Deadline warning.** The submission deadline recorded above (12 September
> 2026) precedes the date this manuscript was prepared. Confirm whether a
> further extension applies, or whether submission is now closed.

---

## 2. Format — NOT VERIFIED; chosen from repository precedent

**No official IC_TORS'26 author template, class file, style file or formatting
instruction was found** in this repository, its archives, or the uploaded
material. A filesystem-wide search for `*.cls`, `*.sty` and template files
returned none for this conference.

The format used here was therefore chosen from the one piece of verifiable
evidence available — **a prior IC_TORS'26 submission present in this
repository**:

| | |
|---|---|
| File | `paper/IC_TORS26_SHAP_MCDM_conference_final_2026-08-27_v11.tex` |
| Document class | `\documentclass[runningheads]{llncs}` (Springer LNCS) |
| Author block | `Anonymous Author(s)` / `Anonymous institution(s)` |
| Compiled length | **12 pages** |

This manuscript matches that class and that anonymisation convention. The
Springer collaboration noted in section 1 is **consistent** with an LNCS-family
template but does **not** confirm it: Springer publishes several series (LNCS,
LNBIP, CCIS, AISC) with different templates.

**Action required:** confirm the official template. If the conference requires a
different Springer series or a Word template, the manuscript body transfers
unchanged; only the preamble and the bibliography style need substitution.

---

## 3. Page limit — NOT VERIFIED

**No page limit for IC_TORS'26 was found.** None is invented here.

| | |
|---|---|
| This manuscript | **27 pages** in `llncs` |
| Prior IC_TORS'26 submission in this repository | 12 pages in the same class |

The manuscript has **not** been pre-emptively compressed to an unverified
limit, because compressing to an invented number would degrade readability for
no confirmed reason.

**If a limit of 12–15 pages applies**, condense in this order, which removes
presentation before evidence:

1. Move Tables 6 and 7 and Figures 3 and 6 to supplementary material (≈4 pages).
2. Reduce Section 5.6 (Experimental Integrity and Protocol Deviations) to a
   half-page summary, with detail in supplementary material (≈1 page).
   **Retain the disclosure of deviation D-1 and of the infeasible shift split in
   the main text** — these are integrity disclosures, not padding.
3. Merge Sections 6.5 (Noise and Statistical Resolution) and 6.9 (Boundary
   Refinement) into one subsection (≈1.5 pages).
4. Shorten Section 2 to two subsections (≈1 page). Note this conflicts with the
   three-subsection structure if that structure is itself a requirement.

Steps 1–3 reach roughly 20 pages without removing a result. Going below that
requires cutting evidence, which is an authors' decision.

---

## 4. Anonymity — NOT VERIFIED; anonymised anyway

Whether IC_TORS'26 uses double-blind review **could not be verified**. The
manuscript is submitted anonymised (`Anonymous Author(s)`,
`Anonymous institution(s)`), matching the prior submission in this repository.
De-anonymising is a two-line change to the preamble if single-blind or open
review applies.

No acknowledgements, funding statement or author-identifying URL appears in the
manuscript.

---

## 5. Submission format — NOT VERIFIED

The submission system, accepted file formats and whether source files are
required alongside the PDF **could not be verified**. This package provides
LaTeX source, bibliography and figures, which satisfies either a
PDF-only or a source-required submission.

---

## 6. Package contents

```
main.tex            standalone manuscript — no \input of any other .tex file
references.bib      23 references, all cited, all verified against publisher records
figures/            7 vector PDF figures, embedded fonts
TORS_COMPLIANCE.md  this file
```

All tables are contained directly in `main.tex`. All numeric values are inlined
literally; the manuscript depends on no auxiliary macro file.

### Compilation

```
pdflatex main
bibtex   main
pdflatex main
pdflatex main
```

Verified from a clean directory: **0 errors, 0 undefined citations, 0 undefined
references, 0 overfull boxes above 15 pt, 27 pages.**

Requires `llncs.cls` and `splncs04.bst`. On Overleaf these are available by
selecting a Springer LNCS template, or by adding the two files to the project.
On TeX Live they are in the `texlive-publishers` package.

Set `main.tex` as the Overleaf main document.

---

## 7. Content requirements confirmed in this manuscript

| Requirement | Status |
|---|---|
| Top-level order: Introduction, Literature Review, Problem Formulation, Methodology, Experiments, Results and Discussion, Conclusion | satisfied, verified programmatically |
| Exactly three Literature Review subsections | satisfied |
| No top-level Discussion, Limitations, Integrity, Reproducibility or Future Work section | satisfied — integrated into 5.6, 6.12 and the Conclusion |
| Protocol deviation D-1 disclosed, screen not described as passing | satisfied, Section 5.6 |
| Infeasible shift split and replacement disclosed | satisfied, Section 5.6 |
| Adaptation headroom stated as 0.451 s/vehicle and 0.095% of the single-best fixed policy's mean, not as a physical travel-time improvement | satisfied, Section 6.3 |
| Distribution-shift claim matches the table (helps 2, indistinguishable 3, harms 3) | satisfied, Section 6.8 |
| Support gate not presented as a general out-of-distribution guarantee; O8 blind spot retained | satisfied, Sections 4.6 and 6.8 |
| No claim of statistical significance | satisfied — a paired resolution criterion is reported instead, Section 4.7 |
| No version, redesign or previous-study language | satisfied, verified programmatically |
