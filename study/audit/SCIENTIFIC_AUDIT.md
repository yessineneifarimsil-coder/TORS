# Scientific Audit

Generated from `results/results.json`. Every number here is the number the
analysis produced; nothing is transcribed by hand.

## 1. Data integrity

| | |
|---|---|
| Runs executed | 12,960 |
| Runs failed | 0 |
| Contexts designed | 648 |
| Contexts analysed | 648 |
| Contexts excluded, invalid | 0 |
| Contexts excluded, incomplete | 0 |
| Minimum completion rate | 1.0000 |
| Mean completion rate | 1.0000 |
| Total teleports | 0 |

Validity rule, declared in the frozen specification: completion >= 0.98 and teleports == 0, declared in the frozen spec.
Completeness rule: a context is analysed only if all 4 policies have 5 valid seeds.

Every run record is a line of `results/main.jsonl` containing its full job
specification, so any reported value can be traced to the run that produced it.
`campaign.py` keys resumption on the full specification, so a re-run reproduces
the same set.

## 2. Leakage audit

| Risk | Control | Verified by |
|---|---|---|
| Outcome used as a feature | the eight descriptors are functions of the context definition only and cannot be computed from an outcome | `common.descriptors` takes no outcome column |
| Test outcomes in training | leave-one-context-out; the held-out context contributes nothing | `policy_selectors.loco` builds the training index by exclusion |
| Same context's seeds split across train and test | the context, not the run, is the unit; all seeds move together | `matrices` aggregates to one row per context before splitting |
| Preprocessing fitted on all data | standardisation, SBS identity, tree thresholds, conformal quantiles and the support envelope are all recomputed inside each fold | `policy_selectors.fit_predict` receives only the training index |
| SBS chosen with test knowledge | SBS is `argmin` of the mean cost over training contexts only | same |
| Hyperparameters tuned on test | fixed in the frozen specification before any evaluation run | `spec/FROZEN_SPEC.md` §8, committed before the campaign |
| Future information as a predictor | policies read link travel times no newer than `t - lag`; the incident realisation is never exposed | `policies.Observatory._visible`; test 1 in `tests/test_policies.py` |

## 3. Policy audit

12 known-answer tests plus a two-path in-simulator integration test, all
passing. The tests establish that the observation lag hides newer samples, that
the free-flow fallback engages before any admissible sample, that P1 ignores
congestion entirely, that P2 follows the observed mean, that P4 prefers the
steadier of two paths with equal means and reduces to P2 at lambda = 0, that P3
respects its admissibility tolerance and splits equal-cost paths in proportion
to capacity, and that a degenerate assignment window is refused rather than
silently absorbed. Inside the simulator, P3 splits demand 1.97 against a
capacity ratio of 2.00 while P1 commits the whole cohort to one path.

## 4. Seed and pairing audit

Seeds per cell: [5]. Common random numbers: the
vehicle set, departure times, guided/unguided labelling, habitual corridor,
background traffic and the incident realisation are functions of the seed and
context alone. The experimental unit is the context. A difference is claimed
only when the paired seed difference exceeds twice its standard error; the mean
noise floor is 20.90 s of journey time.
Unresolved differences are reported as ties, and the number of them is reported
rather than suppressed: 391 of 648 contexts.

## 5. Metric audit

Capacity is measured, not assumed: 1761 veh/h/lane
on the arterial, 1596 on the slower street,
1500 veh/h uninterrupted on the bypass.

Criterion alignment across the analysed contexts:

| pair | pooled r | identical policy ordering |
|---|---|---|
| journey time vs CO2 | +0.9390 | 52% |
| journey time vs stopped delay | +0.8916 | 34% |
| CO2 vs stopped delay | +0.8948 | 34% |

The best policy on CO2 differs from the best on journey time in
192 contexts
(30%); on stopped delay,
363 (56%).

Three quantities are kept distinct throughout and never substituted: top-1
selection accuracy, the policy ranking, and decision regret in seconds.

## 6. Baseline audit

Single best policy: **P3**, optimal in 65%
of contexts. Mean cost 474.4 s against the hindsight best
473.9 s, so the headroom available to any selector is
0.45 s per vehicle (0.12%), with a
maximum of 17.2 s in a single context.

| selector | mean regret (s) | median | max | within noise | gap closed vs SBS |
|---|---|---|---|---|---|
| B0_SBS | 0.45 | 0.00 | 17.2 | 99% | -- |
| B1_mechanistic | 0.77 | 0.00 | 17.2 | 96% | -0.714 |
| B2_tree3 | 0.34 | 0.00 | 17.2 | 99% | 0.238 |
| B3_logit | 0.28 | 0.00 | 17.2 | 100% | 0.373 |
| B4_GBDT | 0.20 | 0.00 | 7.0 | 100% | 0.558 |
| B5_selective | 0.45 | 0.00 | 17.2 | 99% | 0.000 |
| VBS_reference | 0.00 | 0.00 | 0.0 | 100% | 1.000 |

VBS is retrospective and is not deployable; it appears only as an upper
reference. The primary comparison is B4 against B1.

## 7. Distribution-shift audit

| split | held out | shift type | B0 | B1 | B4 | B5 | flagged | abstained |
|---|---|---|---|---|---|---|---|---|
| O1_demand_high | demand = 4200.0 | extrapolation | 0.00 | 2.35 | 0.98 | 0.00 | 43% | 17% |
| O2_demand_low | demand = 1200.0 | extrapolation | 0.53 | 0.52 | 0.53 | 0.53 | 15% | 75% |
| O3_demand_mid | demand = 2400.0 | interpolation | 0.56 | 0.64 | 0.17 | 0.56 | 0% | 25% |
| O4_lag_long | lag = 300.0 | extrapolation | 0.23 | 0.66 | 0.24 | 0.23 | 100% | 38% |
| O5_penetration | penetration = 0.8 | extrapolation | 0.30 | 6.15 | 0.29 | 0.30 | 100% | 14% |
| O6_green_high | gc = 0.65 | extrapolation | 1.04 | 3.68 | 1.16 | 1.04 | 100% | 51% |
| O7_incident | incident = 1.0 | covariate + concept shift | 0.63 | 5.33 | 2.22 | 0.63 | 32% | 36% |
| O8_northcorridor | incident located on the north corridor | domain shift | 0.31 | 0.29 | 0.18 | 0.31 | 0% | 31% |

No coverage guarantee is claimed on any of these splits. Split conformal
coverage requires exchangeability, which covariate shift breaks; the conformal
gate is calibrated in-distribution and heuristic outside it, the support gate is
what addresses extrapolation, and neither detects concept shift.

## 8. Sensitivity audit

Preference profiles change the preferred policy in 14.5% of contexts. Under P3, changing p3_eps from 0.2 to 0.1 shifts mean journey time by +8.10 s (+1.27%), 0.3 shifts mean journey time by -16.66 s (-2.62%). Under P4, changing p4_lambda from 1.0 to 0.5 shifts mean journey time by -0.11 s (+0.00%), 1.5 shifts mean journey time by +1.27 s (+0.16%).

## 9. Reproducibility audit

| Item | Status |
|---|---|
| SUMO version | 1.27.1, pinned in `README.md` |
| Network files | generated by `scenario/build_net.py`, committed |
| Demand generation | `sim/demand.py`, deterministic in (demand, penetration, seed) |
| Policy implementation | `policies/policies.py`, committed, unit-tested |
| Run records | `results/*.jsonl`, one line per run with full specification |
| Analysis pipeline | `analysis/run_analysis.py` -> `results/results.json` |
| Manuscript numbers | `analysis/emit_numbers.py` -> `paper/numbers.tex` |
| Figures | `figures/*.py`, all reading `results.json` or the run records |
| Specification freeze | `spec/FROZEN_SPEC.md`, committed before the campaign |
| Protocol deviations | `results/SCREENING_REPORT.md`, deviation D-1 |
