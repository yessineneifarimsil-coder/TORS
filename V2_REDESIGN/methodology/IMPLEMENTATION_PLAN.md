# Implementation Plan

Ordered, with gates. Effort is indicative, not a commitment.

| Phase | Tasks | Output | Gate |
|---|---|---|---|
| **0. Literature & specification** | Close L1–L12 in `literature/LITERATURE_MAP.md`; source VOT/VOR/carbon; read Pan et al. (2013) in full for the P3 variant; write exact math for P1–P4 | `policies/` specs final | Every policy has a primary-source formulation; no "to be sourced" rows remain |
| **1. Implementation & validation** | Install SUMO (record version); build the frozen network; implement P1–P4; known-answer unit tests; verify common random numbers | Tested policy code | All four unit tests pass; CRN asserted, not assumed |
| **2. Complementarity screen** | 12–16 contexts × 4 policies × ≥10 seeds; run `screening_scaffold.py` | `reports/SCREENING_REPORT.md` | **G1–G4. Stop/go.** |
| **3. Freeze** | Commit network, factor levels, policy parameters, metric, baselines, splits, analysis plan | Pre-registration file | Committed before any Phase 4 run |
| **4. Main campaign** | Full factorial or fractional design × ≥5 seeds | Run table | All runs complete; no post-hoc network edits |
| **5. ML** | Features + leakage audit; GBDT advantage model; conformal calibration; support gate | Trained model + written leakage audit | Audit passes; test set untouched |
| **6. Evaluation** | Baseline ladder B0–B5 + cross-fitted VBS; seven OOD splits reported separately | Results tables | Test set opened exactly once |
| **7. Statistics** | Context-level inference; risk–coverage; harm rate; CVaR₉₀ | Statistical appendix | — |
| **8. Write-up** | Manuscript; honest reporting of whichever way B4-vs-B1 goes | V2 paper | — |

## Reused from V1

The decision-analysis machinery in `../routing_regime_study/analysis/` — regret, headroom, hindsight
benchmark, grouped splits, and the hyperparameter/seed/weight/scaling robustness battery — is
audited, correct, and generalises directly. It is copied into V2 and extended, never edited in place.

## Not reused

No V1 simulation asset (none exists in this project), no V1 run, no V1 number. V2 evidence comes
from V2 experiments only.

## Compute

The screen is small by construction (≈500 runs). The main campaign is sized **after** the screen
reports its noise floor, because required replication depends on the measured effect sizes. Sizing
it now would be guessing.
