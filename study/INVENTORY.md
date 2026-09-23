# Research and Data Inventory (Phase A)

Audit date: 2026-09-23. Environment: Linux x86_64, 4 cores, 15 GB RAM, 27 GB free disk.

## A.1 Computational environment — VERIFIED PRESENT

| Component | Status | Version |
|---|---|---|
| SUMO (`sumo`, `netconvert`, `duarouter`, `netgenerate`) | present | 1.27.1 |
| TraCI / sumolib Python bindings | present | 1.27.1 |
| Python | present | 3.11.15 |
| numpy / scipy / pandas / scikit-learn | present | 2.4.6 / 1.17.1 / 3.0.6 / 1.9.1 |
| LightGBM (GBDT) | present | 4.7.0 |
| matplotlib | present | 3.11.2 |
| pdfLaTeX | present | TeX Live 2023 |

SUMO was not present at session start; it was installed from the Eclipse SUMO PyPI
wheel. The binary is verified to execute. **The simulation study is therefore
executable in this environment.**

## A.2 Pre-existing evidence — WHAT EXISTS

| Asset | Location | Content |
|---|---|---|
| Run table | `analysis/runs.csv` | 432 rows: 24 contexts x 6 policies x 3 seeds |
| Workbook | uploaded `.xlsx` | 22 sheets incl. NETWORK (47 links), SCENARIO_DESIGN, RAW_PERFORMANCE (444 rows), PILOT_RESULTS |
| Manuscript | `paper/main.tex`, Overleaf zip | 15 pp, 25 references |
| Analysis scripts | `analysis/*.py` | 17 scripts, all re-runnable against `runs.csv` |
| Figures | `paper/figures/` | 4 vector PDFs |

## A.3 Protocol compatibility — THE DECISIVE FINDING

The question is not whether this evidence is *valid*; it is whether it is
*poolable* with the study specified here. It is not. Five independent blockers:

1. **No simulation assets exist.** Repository-wide search for `*.net.xml`,
   `*.rou.xml`, `*.sumocfg`, `*.nod.xml`, `*.edg.xml`, `*.add.xml` returns
   **zero files**. The environment that produced the 432 runs cannot be
   reconstructed, inspected, or extended. Its capacities, signal programs and
   demand profiles are known only through summary statistics.
2. **Factor coverage.** Four of the six factors required here — guidance
   penetration, information lag, incident state, alternative-capacity ratio —
   are absent. They are not merely unvaried; the recorded design has no column
   for them, so the existing runs cannot even be labelled as a corner of the
   new design.
3. **Portfolio.** The recorded portfolio is {shortest path, dynamic travel
   time, eco, three time-constrained eco variants}. It contains neither a
   capacity-aware load-balancing policy nor a reliability-aware policy, which
   are two of the four policies under study.
4. **Seeds.** Three seeds per cell, against a minimum of five.
5. **Objective.** The recorded decision used a two-criterion additive scalar
   with fixed reference scales. This study uses three criteria with a
   Pareto-first procedure.

**Disposition.** The 432 runs are retained as internal hypothesis-generating
material and are cited nowhere as evidence. No number from them appears in the
manuscript. Pooling measurements taken on an unreconstructible network with
measurements taken here would be a data-integrity failure, not a saving.

The one element that *is* carried forward is a definition, not a datum: total
stopped delay, mean journey time and CO2 were already measured with the
definitions used here, which is why those three criteria are adopted.

## A.4 What is missing and is not fabricated

| Missing | Consequence |
|---|---|
| Network/route/config files for the 432 runs | Environment rebuilt from scratch and fully specified here |
| Conference template and page limit | Manuscript formatted generically; compliance unverified |
| Author and affiliation details | Placeholder retained |

## A.5 Consequence for the study design

The scenario environment is built from scratch in `scenario/`, with every node,
edge, lane count, speed limit, signal program and demand profile defined by
scripts committed in this repository. Every number reported downstream is
produced by those scripts from simulation output written in `results/`.
