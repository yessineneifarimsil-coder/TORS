# Journal Compliance

What was verified about the target journals, what could not be, and what the
manuscript does about it. **No formatting requirement, page limit, word limit or
submission rule is invented here.**

---

## 1. What could not be verified, and why

**All publisher and indexing domains are blocked by this environment's network
egress proxy.** Direct fetches were attempted and refused for
`sciencedirect.com`, `elsevier.com`, `ieee-itss.org`, `scimagojr.com`,
`doi.org` and `arxiv.org`. The official guide for authors of every candidate
journal is therefore **unread**.

Everything in Section 2 comes from web-search result summaries, which are
secondary. Every row must be confirmed against the journal's own guide for
authors before submission.

In particular:

- **No quartile is asserted.** Journal quartiles change annually, are
  database-specific, and could not be checked.
- **No word or page limit is asserted as binding.** A secondary source
  associated "about 8,000 words" with Transportation Research Part C; that
  figure could not be confirmed against Elsevier and is **not** treated as a
  requirement. Section 4 reports the manuscript's actual length so the author
  can compare it against the real guideline.

---

## 2. Candidate journals, on scientific fit

Ranked by fit to the paper's content, not by prestige.

### 2.1 Transportation Research Part C: Emerging Technologies (Elsevier) — recommended

| | |
|---|---|
| Scope (from search summaries) | development, application and implications of emerging technologies in transportation systems; explicitly includes transport engineering, simulation, operations research and traffic flow |
| Fit | strong. The paper is a controlled microsimulation study of route-guidance policy selection, framed as an operations-research decision problem, with an ITS deployment question at its centre. All four of the named interest areas apply. |
| Article type | full-length research article |
| Format used here | Elsevier's own `elsarticle` class, `[preprint,12pt]`, with `elsarticle-harv` author–year bibliography |
| Unverified | word limit, structured-abstract requirement, declaration set, data-availability policy, highlights, graphical abstract, APC |

**Why this one.** The paper's contribution is a measurement about when an
intelligent routing layer is worth deploying, which is a transport-systems
implication of an emerging technology rather than a methodological advance in
learning or in traffic theory. It needs room for seven figures, seven tables and
a distribution-shift analysis, which a page-limited venue would not give it.

### 2.2 IEEE Transactions on Intelligent Transportation Systems — possible, with compression

| | |
|---|---|
| Scope (from search summaries) | all scientific and technical aspects of intelligent transportation systems, including modelling, simulation and evaluation |
| Fit | good on subject; the selective-prediction and distribution-shift material sits well in an ITS venue |
| Constraint | regular papers are normally **10 transaction pages**, extendable by up to six at a stated per-page charge (search summary; unverified) |
| Consequence | the manuscript would need substantial compression. The shift taxonomy, the campaign ledger and the limitations section are the parts that a page limit would force out, and they are the parts the paper's integrity depends on. |

### 2.3 Journal of Intelligent Transportation Systems (Taylor & Francis) — possible

Subject fit is good and length constraints are typically looser than IEEE's.
Scope and requirements were not verified at all and would need checking from
scratch.

### 2.4 Transportation Research Part B: Methodological — not recommended

Part B is methodological. This paper contributes a measurement and a set of
distinctions, not a method or a model, and would be out of scope.

---

## 3. Formatting decisions and their basis

| Decision | Basis |
|---|---|
| `\documentclass[preprint,12pt]{elsarticle}` | Elsevier's own submission class, available in TeX Live; not a guideline read from the journal |
| `elsarticle-harv` (author–year) | Elsevier's own Harvard style for the `elsarticle` family; Part C uses author–year in published articles |
| Anonymous front matter | **precautionary.** Part C is single-blind by default according to secondary sources, but this was not verified, so the manuscript is prepared anonymised. See Section 5. |
| Figures as vector PDF at 390 pt native width | drawn at the class's text width so text renders at true size rather than being downscaled |
| Tables inline, floats near their citations | readability for review; Elsevier accepts either this or end-placed floats |

Nothing in the preamble encodes a requirement that was not verified.

---

## 4. Manuscript metrics

Measured on the compiled PDF and source.

| | |
|---|---|
| Pages | 42 in `elsarticle` `preprint,12pt` (a deliberately loose single-column preprint format; the typeset two-column article would be substantially shorter) |
| Body prose | ~10,700 words, excluding front matter, floats, captions and references |
| Abstract | 281 words |
| Figures | 7 |
| Tables | 7 |
| References | 25, of which 23 were verified against primary records in a previous audit and 2 are preprints verified by reading them |
| Compilation | 0 errors, 0 undefined references, 0 undefined citations, 0 missing figures, 1 overfull box of 2.6 pt in a page footer |

**If a word limit applies,** the abstract is already within a 250–300 word band
but may need trimming to a stated maximum, and the body would need reduction.
The reductions that cost least scientifically, in order:

1. Merge Sections 7.1 and 7.2 of the Discussion, which restate the Results
   before interpreting them (≈500 words).
2. Move the campaign ledger (Table 3) and Section 5.6 on experimental integrity
   to supplementary material, retaining a two-sentence summary and a pointer
   (≈700 words). **This is a genuine loss** — the protocol deviation is material
   to how the reader should weigh the complementarity result — and should be the
   last resort, not the first.
3. Reduce Section 6.9 (sensitivity) to the two findings that are used later, the
   P3 tolerance and the preference profiles (≈300 words).

Do **not** reduce Section 6.7 (distribution shift), Section 6.8 (selective
prediction) or Section 7.7 (limitations) to meet a limit; they carry the paper's
negative results and its scope statements.

---

## 5. Anonymity

Prepared anonymised, because the review model could not be verified:

```latex
\author{Anonymised for review}
\address{Affiliations withheld for review}
```

If review is single-blind, replace those two lines with the author list,
affiliations and corresponding-author email in the usual `elsarticle` form.
Nothing else in the manuscript identifies the authors: there is no
acknowledgements section, no funding statement, and no self-citation. See
`ARTICLE_1_ARTICLE_2_OVERLAP.md` Section 5 for how the companion article must be
disclosed, which is a separate obligation from anonymity.

---

## 6. Declarations still required

These are standard for Elsevier submissions and could not be drafted here
because they depend on facts only the authors hold:

- author contributions (CRediT taxonomy)
- declaration of competing interests
- funding sources
- data availability statement — a draft is in `REPRODUCIBILITY.md`; the
  repository DOI must be inserted
- declaration of generative-AI use in the writing process, if the journal
  requires one
- suggested reviewers, if requested

---

## 7. Pre-submission checklist

- [ ] Retrieve the target journal's guide for authors and re-check every row of
      Sections 2 and 3 of this file
- [ ] Confirm the review model and de-anonymise if single-blind
- [ ] Confirm the word or page limit and apply Section 4 if one binds
- [ ] Decide the disclosure treatment of the companion article and apply it
- [ ] Insert the repository DOI in the data-availability statement
- [ ] Measure and insert the campaign wall-clock time in `REPRODUCIBILITY.md`
- [ ] Complete the declarations in Section 6
- [ ] Confirm figure format and resolution requirements (vector PDF is supplied)
