# Supervisor Package — Regime-Dependent Routing-Policy Preference

Final version. **The scientific scope is frozen.** Nothing in this package contains a new
experiment, strategy, scenario, method, figure or table relative to the completed study.
All results come from the **432 completed SUMO runs** already in the workbook.

---

## Present this in the following order

1. **`SUPERVISOR_BRIEFING/briefing.pdf`** — 2 pages. **Start here.** Page 1 is what changed and
   why; page 2 answers the ten questions most likely to be asked.
2. **`FINAL_MANUSCRIPT/main.pdf`** — 15 pages. The paper itself.
3. **`DATA_AND_ANALYSIS/`** — open only if a number is challenged.

---

## What each file is

### `FINAL_MANUSCRIPT/`
| File | What it is |
|---|---|
| `main.tex` | **The manuscript source.** Single self-contained LaTeX file. |
| `main.pdf` | The compiled 15-page manuscript. |
| `figures/network.pdf` | Fig. 1 — the 12-signal development network |
| `figures/regime_structure.pdf` | Fig. 2 — **the key figure.** (a) switching margin vs demand; (b) hindsight-best policy per context |
| `figures/decision_outcome.pdf` | Fig. 3 — (a) regret by method; (b) out-of-regime extrapolation |
| `figures/forecast_and_decision.pdf` | Fig. 4 — the environmental negative control |

**No `.bib` file exists and none is needed.** The 25 references are written directly into
`main.tex` as a `thebibliography` environment (line ~317). A single `pdflatex` pass chain builds
the document; there is no BibTeX/biber step.

**No custom `.cls` or `.sty` files exist and none are needed.** `main.tex` uses the standard
`article` class and packages shipped with any normal TeX Live / MiKTeX installation
(`lmodern`, `microtype`, `amsmath`, `amssymb`, `booktabs`, `tabularx`, `graphicx`, `float`,
`xcolor`, `caption`, `hyperref`, `url`, `geometry`, `fontenc`, `inputenc`).

**To compile:** from inside `FINAL_MANUSCRIPT/`, run `pdflatex main.tex` **twice** (the second
pass resolves cross-references). `\graphicspath{{figures/}}` resolves the figures relatively, so
the folder is portable as-is.

### `SUPERVISOR_BRIEFING/`
`briefing.pdf` (2 pp) and its source `briefing.tex`. Compiles the same way.

### `DATA_AND_ANALYSIS/`
| File | What it is |
|---|---|
| `Routing_Strategy_Selection_Regime.xlsx` | The audited workbook — 25 sheets |
| `CURRENT_STUDY_STRENGTHENING_REPORT.md` | The mechanism, regime, ML, OOD and MCDM analyses behind §4 of the paper |
| `results.json` | **Every headline number the paper reports**, machine-readable |
| `runs.csv` | The 432-run table (one row per completed simulation) that all analysis reads |

---

## Which Excel sheets to open in discussion

The workbook has 25 sheets; these five carry the discussion:

| Sheet | Use it for |
|---|---|
| **`REGIME_TRANSITION`** | The switching margin per cell, crossing brackets, seed stability. **Open this first.** |
| **`DECISION_EVALUATION`** | Fixed vs adaptive vs hindsight regret; the extrapolation stress test; per-context decisions |
| **`NEGATIVE_CONTROLS`** | Why ECO was dropped; why the preference weights change nothing; insertion-delay check |
| `REDESIGN_RESULTS` | The 144 context-setting means behind every aggregate |
| `RAW_PERFORMANCE` | One row per completed run, if a single number is queried |

The remaining 22 sheets are the original audited workbook and are **unmodified**.

---

## Where the main numerical results are

Fastest route to any number: **`DATA_AND_ANALYSIS/results.json`**.

The five that matter most:

| Quantity | Value |
|---|---|
| Available headroom `H̄` (mean regret of the best fixed policy, DTT) | **0.03018495** |
| Adaptive selector regret, leave-one-context-out | **0.00605893** |
| Fraction of headroom captured | **0.79927 (79.9%)** |
| Extrapolation above training support (hold out 1680 veh/h) | **0.14856** vs **0.00000** for fixed DTT |
| Contexts where the selector is optimal | **21 / 24** |

**79.9% is the fraction of available decision headroom captured relative to the fixed baseline.**
It is not a travel-time saving, not a CO₂ reduction, not prediction accuracy, and not feature
importance. Physically the same comparison is 13.0 s and 30.7 g per vehicle.

---

## Scope statement

- No new routing strategy, scenario, criterion, MCDM method or ML method
- No new simulation — the 432 runs are the same ones already audited
- 4 figures, 2 tables, unchanged
- Held-out evaluation is leave-one-context-out; **no independent external confirmation set exists**
- The demand grid brackets the transition (480 veh/h spacing); **no threshold is estimated**
- The signal-regime result is an observed displacement, **not a causal claim**
- Synthetic benchmark — **no real-city validation is claimed**

## Still open (needs a decision)

1. **Conference template and page limit** — none was supplied, so the manuscript uses a generic
   A4 layout. Format compliance is unverified and is not claimed anywhere in the paper.
2. **Author block** — currently the placeholder `Author details to be supplied`.
