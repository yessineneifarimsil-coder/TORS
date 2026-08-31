# Controlled XAI–MCDM benchmark for ITS prioritisation

Research repository for the conference paper
**“From Predictive Importance to Decision Value: Evaluating XAI-Based Weights for
ITS Prioritisation.”**

## What this study is

A controlled synthetic benchmark that asks a *prior* question about the now-common
pipeline `predictive attribution → global criterion weight → MCDM ranking`: before
comparing weighting methods at scale, can the benchmark itself demonstrate that
competing decision pipelines add value over meaningful simple references?

The laboratory has six ITS alternatives, ten criteria, a nonlinear oracle, XGBoost,
interventional TreeSHAP, six structured global-weight methods (oracle attribution,
SHAP, permutation importance, Ridge+, CRITIC, entropy) and benefit-oriented MOORA,
with Equal, RandomWeights and MajorityWinner as diagnostic references.

## Scientific state: v1 is CLOSED

- A structural audit found that the original response generator's contextual variation
  **cancelled exactly** under the normalization used by the decision operator. The
  corrected monotone **D29 kernel** removed that algebraic collapse.
- **Pilot B** — a five-world adequacy gate frozen *before* execution — was run once at
  one authorized development condition, `(N, c, rho, lambda) = (250, 0.30, 0.4, 0.5)`,
  over development worlds 21001–21005.
- Four structured methods, including SHAP, **cleared** the prospectively specified
  RandomWeights adequacy criterion. **No** structured method cleared the
  MajorityWinner criterion; closed-form oracle attribution also failed it.
- The `modal_winner_effective_tie` hard stop fired. **The protected primary factorial
  was therefore never authorized and never run.**

> There are **no primary results** in this repository. Primary worlds (11001–11030) and
> reserve worlds (30001–30005) were never accessed. Every directory labelled
> *archived* holds an unexecuted protocol, not a result.

One **post-closure descriptive diagnostic** reconstructed the 7000 context-level
selections of the seven frozen fixed-weight vectors. It is descriptive and
non-confirmatory: it cannot modify, reinterpret or reopen the Pilot-B gate.

## Repository layout

### Frozen scientific record — read-only

Do not edit anything below. These files are the study's evidence, and the manuscripts
are checked against them.

| Path | Contents |
|---|---|
| `results/` | Frozen result artefacts (Pilot B, post-closure diagnostic, D29 geometry, B100, calibration, candidate screening) |
| `config/` | Frozen protocols, thresholds, seed definitions |
| `docs/` | Frozen protocol and result records |
| `src/` | Generator, evaluators, executors, weighting methods, MCDM operators |
| `tests/` | Software test suite for the above |
| `archives/` | Immutable submission and reproducibility archives |

### Manuscript and presentation — editable

| Path | Contents |
|---|---|
| `paper/` | Manuscript sources. Current: `*_final_2026-08-29_v12.tex` (main) and `*_supplement_2026-08-29_v5.tex`. Earlier versions are kept as historical records and are not maintained. |
| `scripts/paper/` | Read-only verification, table, figure and audit scripts |
| `outputs/paper/` | Everything those scripts generate (figures, tables, PDFs, audit reports, manifest) |

`scripts/paper/_frozen.py` refuses at runtime to write into any protected directory, so
the manuscript tooling cannot modify the scientific record.

## Building the manuscripts

Both `.tex` files default to the **anonymous review** build. The identified
camera-ready build comes from the same source:

```bash
cd paper
pdflatex IC_TORS26_SHAP_MCDM_conference_final_2026-08-29_v12.tex          # anonymous
pdflatex "\def\CAMERAREADY{1}\input{IC_TORS26_SHAP_MCDM_conference_final_2026-08-29_v12}"
```

The main paper needs `outputs/paper/figures/decision_value_figure.pdf`; generate it
first with the figure script below.

## Reproducing the reported numbers, tables, figure and checks

```bash
python scripts/paper/verify_frozen_manuscript_numbers.py   # every printed number vs the frozen record
python scripts/paper/check_selection_map_consistency.py    # re-derive all 7000 archived selections
python scripts/paper/build_pilot_b_tables.py               # regenerate manuscript tables
python scripts/paper/make_decision_value_figure.py         # regenerate the results figure
python scripts/paper/manuscript_consistency_audit.py       # framing, labelling, terminology, LaTeX hygiene
python scripts/paper/latex_preflight.py                    # compile both papers in both modes; anonymity audit
python scripts/paper/build_reproducibility_manifest.py     # anonymous content manifest
```

Each exits non-zero on disagreement. None of them repairs a number: a mismatch is a
finding to report, not something to adjust.

Benchmark worlds are regenerated deterministically from the frozen seeds and
configurations rather than stored, so `data/generated/` and `results/weights/` are
empty by design.

## Environment

Python 3.11; see `environment.yml` and `environment.lock.yml`. The manuscript scripts
need only the standard library plus `matplotlib` (figure) and a LaTeX installation
providing `llncs.cls` (preflight).

## Reusing this work

Pilot B v1 is closed and must not be rerun. Any follow-up must be specified as a
separately versioned study that discloses this closed result; it cannot alter the v1
thresholds, result or closure reference.
