# Context-Dependent Selection Among Established Urban Routing Policies

Complete study: scenario, policies, experiment, analysis, figures, manuscript.
Every number in the manuscript is produced by the scripts here from simulation
output in `results/`.

## Layout

```
spec/       FROZEN_SPEC.md          the experiment specification, frozen before any evaluation run
            screen_design.json      the 16 screening contexts
scenario/   build_net.py            builds the network; agb_alt{1,2}.net.xml are its output
policies/   policies.py             P1-P4 and the shared observation buffer
sim/        demand.py               deterministic demand generation (common random numbers)
            run.py                  one run = one (context, policy, seed)
            campaign.py             parallel driver, resume-safe
            mkjobs.py               job-list generation
tests/      test_policies.py        12 known-answer tests
            test_twopath.py         two-path SUMO integration test for load balancing
            test_capacity.py        capacity calibration and validation
analysis/   common.py               loading, context aggregation, pairing, Pareto, regret
            policy_selectors.py     baselines B0-B5, gates, LOCO
            ood.py                  distribution-shift splits
            screen_gates.py         the four screening gates
            run_analysis.py         -> results/results.json  (single source of every number)
            emit_numbers.py         -> paper/numbers.tex     (every manuscript macro)
            tables.py               -> paper/tables/*.tex
figures/    style.py, fig*.py       the nine figures
paper/      main.tex, references.bib, numbers.tex, tables/, figures/
audit/      the scientific audit, literature audit, contribution map, reviewer attack list
results/    *.jsonl run records, results.json, screening report
```

## Reproducing

Requires Python 3.11 and SUMO 1.27.1 (`pip install eclipse-sumo==1.27.1 sumolib
traci`), plus `numpy scipy pandas scikit-learn lightgbm matplotlib`.

```bash
export SUMO_HOME=$(python3 -c "import sumo,os;print(os.path.dirname(sumo.__file__))")

# 1. build the network and validate it
python3 scenario/build_net.py
python3 tests/test_policies.py        # 12 known-answer tests
python3 tests/test_twopath.py         # load-balancing integration test
python3 tests/test_capacity.py        # capacity calibration -> results/capacity_calibration.json

# 2. screen (640 runs) and evaluate the pre-declared gates
python3 sim/mkjobs.py screen results/screen_jobs.json
python3 sim/campaign.py --jobs results/screen_jobs.json --out results/screen.jsonl --workers 4
python3 analysis/screen_gates.py

# 3. main campaign (12960 runs) and the two follow-on campaigns
python3 sim/campaign.py --jobs results/main_jobs.json       --out results/main.jsonl       --workers 4
python3 sim/campaign.py --jobs results/ood_bypass_jobs.json --out results/ood_bypass.jsonl --workers 4
python3 sim/campaign.py --jobs results/sens_jobs.json       --out results/sens.jsonl       --workers 4

# 4. analysis, numbers, tables, figures, manuscript
python3 analysis/run_analysis.py
python3 analysis/emit_numbers.py
python3 analysis/tables.py
python3 figures/fig1_network.py && python3 figures/fig2_portfolio.py && python3 figures/fig3_design.py
python3 figures/figs_results.py
cd paper && pdflatex main && bibtex main && pdflatex main && pdflatex main
```

`campaign.py` is resume-safe: re-running it skips work already present in the
output file, keyed on the full job specification.

## Determinism and pairing

A run is a pure function of its arguments. The vehicle set, departure times,
guided/unguided labelling, habitual corridor choice, background traffic and the
incident realisation depend on the seed and the context only, never on the
policy. Two runs of a context under different policies therefore face identical
vehicles, so every comparison is paired.

## What the run records contain

Each line of a `*.jsonl` file is one run: all context factors, the three
criteria at system, corridor-cohort and guided-cohort level, route split,
completion rate, teleport count, measured corridor capacities, and the realised
incident. `results/results.json` is the aggregate and is the only input to the
manuscript's numbers.
