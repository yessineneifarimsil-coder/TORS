# Reproducibility

Every number in the manuscript is produced by the scripts described here from
the simulation output in `study/results/`. Nothing is transcribed by hand.

## What exists

| Item | Location | Status |
|---|---|---|
| Frozen experiment specification | `study/spec/FROZEN_SPEC.md` | committed before any evaluation run |
| Screening design | `study/spec/screen_design.json` | complete |
| Network builder and built network | `study/scenario/build_net.py`, `agb_alt{1,2}.net.xml` | complete |
| Policy implementations | `study/policies/policies.py` | complete |
| Demand generation (common random numbers) | `study/sim/demand.py` | complete |
| Single-run driver | `study/sim/run.py` | complete |
| Campaign driver, resume-safe | `study/sim/campaign.py` | complete |
| Job lists for every campaign | `study/results/*_jobs.json` | complete, including the 2,160 infeasible jobs |
| Run records | `study/results/*.jsonl` | complete, one JSON object per run |
| Known-answer and integration tests | `study/tests/` | 12 policy tests, a two-path integration test, capacity calibration |
| Study analysis | `study/analysis/` | complete |
| **Independent verification for this article** | `study/audit2/verify_{core,ladder,ood}.py` | complete |
| **Journal number generation** | `journal/analysis/build_numbers.py` → `numbers.json` | complete |
| **Manuscript numerical audit** | `journal/analysis/audit_manuscript.py` | 118/118 pass |
| Figure generation | `journal/figures/figs.py` | all 7 figures |

## Software

Python 3.11; SUMO 1.27.1 with TraCI (`eclipse-sumo==1.27.1`, `sumolib`,
`traci`); `numpy`, `scipy`, `pandas`, `scikit-learn`, `lightgbm`, `matplotlib`,
`openpyxl`. TeX Live with `elsarticle`.

## Determinism

A run is a pure function of its arguments. The vehicle set, departure times,
guided/unguided labelling, habitual corridor choice, background traffic and the
disruption realisation depend on the seed and the context only, never on the
policy. Two runs of a context under different policies therefore face identical
vehicles, which is what makes every comparison paired. `campaign.py` is
resume-safe and keyed on the full job specification, so a partially completed
campaign can be continued without duplicating or perturbing work.

## Reproducing the results

```bash
export SUMO_HOME=$(python3 -c "import sumo,os;print(os.path.dirname(sumo.__file__))")

# 1. network and validation
python3 study/scenario/build_net.py
python3 study/tests/test_policies.py
python3 study/tests/test_twopath.py
python3 study/tests/test_capacity.py

# 2. campaigns (resume-safe; the main campaign dominates the runtime)
python3 study/sim/campaign.py --jobs study/results/main_jobs.json      --out study/results/main.jsonl      --workers 4
python3 study/sim/campaign.py --jobs study/results/ood_north_jobs.json --out study/results/ood_north.jsonl --workers 4
python3 study/sim/campaign.py --jobs study/results/sens_jobs.json      --out study/results/sens.jsonl      --workers 4
python3 study/sim/campaign.py --jobs study/results/boundary_jobs.json  --out study/results/boundary.jsonl  --workers 4

# 3. verification (does not depend on step 2 being re-run)
python3 study/audit2/verify_core.py      # 27 descriptive quantities
python3 study/audit2/verify_ladder.py    # 648-fold LOCO ladder, ~4 min
python3 study/audit2/verify_ood.py       # 8 shift splits

# 4. numbers, figures, manuscript
python3 journal/analysis/build_numbers.py
python3 journal/analysis/audit_manuscript.py
python3 journal/figures/figs.py
cd journal/manuscript && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

Steps 3 and 4 run from the committed run records alone and take minutes. Step 2
re-runs the simulations and is the only expensive part.

## What cannot be reproduced

The **2,160 failed runs of the planned south-bypass domain shift** cannot be
made to succeed, and should not be: they fail for a structural reason, because
closing a lane on a single-lane corridor disconnects it rather than reducing its
capacity. The job list is retained in `study/results/ood_bypass_jobs.json` and
the failure log in `ood_bypass.log`, so the claim can be checked, but the
campaign has no output file.

## Data availability statement (draft)

> The simulation specification, the complete run-level records for all 18,124
> successful simulations, the analysis and verification code, and the scripts
> that generate every figure and every number in this article are available at
> [repository DOI to be inserted on acceptance]. The study uses no proprietary or
> personal data. Reproducing the analysis from the provided run records requires
> only Python and takes a few minutes; reproducing the run records requires SUMO
> 1.27.1 and approximately [wall-clock time to be measured on the target machine].

Insert the repository DOI and the measured wall-clock time before submission.
Both are marked here because neither can be supplied from this environment.
