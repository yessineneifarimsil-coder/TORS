# Frozen Experiment Specification

**Status: FROZEN.** Everything below was written and committed before any
evaluation run was executed. Nothing in it may be revised in the light of a
result. Where a later observation contradicts a choice made here, the
contradiction is reported, not repaired.

The only simulations executed before this freeze were (a) scenario-validation
runs used to confirm the network behaves like a signalised network and to
*measure* its capacities, and (b) policy unit and integration tests. Section 10
records what those runs changed and what they did not.

---

## 1. Decision problem

A context `s` is a set of traffic conditions known before a routing policy is
activated. A policy `a` is one of four established routing families. The
decision is a map from context to policy, made once per context, before the
context is realised.

* **Level 1** context -> choose one routing policy
* **Level 2** the chosen policy routes individual vehicles by its own objective

Regret of choosing `a` in context `s`, on decision cost `C`:

```
R(s, a) = C(s, a) - min_b C(s, b)
```

## 2. Policy portfolio — FROZEN

| | Policy | Objective | Information used | Intended strength | Hypothesised failure mode |
|---|---|---|---|---|---|
| P1 | Static / shortest | `min_p L(p)` | none | no infrastructure, no instability | loads the shortest corridor past its capacity |
| P2 | Reactive dynamic travel time | `min_p mu_hat_p(t-D)` | lagged link travel times | tracks congestion | moves the whole guided cohort together on stale information |
| P3 | Capacity-aware load balancing | min max-link utilisation over travel-time-admissible paths | lagged link travel times + flows + own recent assignments | spreads load when capacity is uneven | wastes time when there is no capacity shortage |
| P4 | Reliability-aware | `min_p [mu_hat_p + lambda sigma_hat_p]` | lagged link travel times | avoids volatile corridors | over-conservative when variance carries no risk |

**Candidate path catalogue.** Every junction permits straight-through movements
only, so the loopless paths from origin portal to destination portal are exactly
three: C (central arterial), N (north street), S (south bypass). The catalogue
is complete, not a k-shortest approximation.

**Frozen policy parameters.** P3: admissibility tolerance `eps = 0.20`,
assignment window 120 s. P4: `lambda = 1.0`. All: observation window 120 s,
sampling interval 30 s. Free-flow fallback before any admissible sample exists.

**Eco-routing is NOT in the portfolio.** It is admitted only if the
policy-complementarity screen demonstrates genuine time/CO2 decoupling in this
network (gate G2 below). Absent that, a fourth objective that is monotone in
travel time adds a label, not a policy.

## 3. Scenario factors — FROZEN

| Factor | Levels | Mechanism it is there to activate |
|---|---|---|
| Corridor demand `D` (veh/h) | 1200, 1800, 2400, 3000, 3600, 4200 | capacity shortage (v/c 0.31 to 1.10 of measured network capacity) |
| Green ratio `g/C` | 0.35, 0.50, 0.65 | signalised capacity, corridor vs cross-street split |
| Guidance penetration `p` | 0.2, 0.5, 0.8 | herding; size of the cohort a policy actually controls |
| Information lag `D` (s) | 30, 120, 300 | staleness; oscillation |
| Incident regime | none, arterial | travel-time risk |
| Alternative capacity (north lanes) | 1, 2 | whether load balancing has anything to balance |

**648 contexts**, full factorial. Background cross-street demand is held at
300 veh/h per street per direction and is not a factor.

**The incident is stochastic.** When the incident regime is active, one lane
closure is drawn from a declared distribution — edge uniform on {c1, c2, c3},
onset uniform on [600, 1200] s, duration uniform on {300, 600, 900} s — from a
stream seeded by the run seed alone. Within a context and seed the realisation
is identical across all four policies, so pairing is exact; across the five
seeds of a context it differs, so the context carries genuine travel-time risk
that no policy can know in advance.

## 4. Criteria — FROZEN

| | Criterion | Definition | Unit |
|---|---|---|---|
| C1 | Mean journey time | mean over the measured cohort of (insertion delay + in-network time) | s/veh |
| C2 | CO2 emissions | total CO2 over the measured cohort, HBEFA3/PC_G_EU4 | kg |
| C3 | Total stopped delay | total time spent with speed below 0.1 m/s — the time vehicles spend *stationary* in queues | veh-s |

Insertion delay is included in C1. A policy that oversaturates the network
produces vehicles that cannot enter it; excluding their wait would credit the
policy for the queue it caused.

**Cohorts.** Primary is **system-wide**: every vehicle, guided or not,
corridor or cross-street, with intended departure in [300, 1500) s. Secondary
diagnostics: the corridor cohort (all main-OD vehicles) and the guided cohort.

**Primary decision cost = C1 system.** It requires no weights. The three
criteria are analysed by Pareto dominance first; scalarisation is used only for
sensitivity, and only through the three declared normalised preference profiles
below. No monetary value of time, value of reliability or carbon price is used,
because no verified source for them is available in this project and inventing
one would make the result an artefact of the invented number.

Preference profiles for sensitivity, on within-context min-max normalised
criteria (w1, w2, w3): **TIME** (0.70, 0.15, 0.15), **BALANCED**
(0.40, 0.30, 0.30), **ENVIRONMENT** (0.20, 0.55, 0.25).

## 5. Seeds, pairing and the noise floor — FROZEN

Five seeds per context (1001-1005). Common random numbers: the vehicle set,
departure times, guided/unguided labelling, habitual corridor assignment,
background traffic and the incident realisation are functions of the seed and
the context only, never of the policy.

The experimental unit for policy selection is the **context**, not the vehicle.

An advantage of `a` over `b` in context `s` is **resolved** when, over the
paired seed differences `d_i = C1(s,a,seed_i) - C1(s,b,seed_i)`,

```
|mean(d)| > 2 * sd(d) / sqrt(n)
```

Unresolved differences are treated as ties throughout.

**Run validity.** A run is valid if completion >= 0.98 and teleports = 0. A
context is valid if all of its runs are valid. Invalid contexts are reported
and excluded; they are not silently dropped.

## 6. Screening gates (STOP/GO) — FROZEN

Evaluated on a 16-context screening subset with 10 seeds, before the main
campaign, on C1 system.

* **G1 — complementarity.** At least 3 of the 4 policies are strictly best in
  at least one screening context, with the advantage over the runner-up
  *resolved* per section 5.
* **G2 — criterion conflict.** At least 25% of screening contexts have a
  non-singleton Pareto set over (C1, C2, C3).
* **G3 — non-degeneracy.** Averaged over the six policy pairs, the fraction of
  contexts in which the pair produces effectively identical outcomes
  (|dC1| within the noise floor AND route splits differing by < 2% of the
  guided cohort) does not exceed 0.50.
* **G4 — multi-factor structure.** The winner map is not reproduced in >= 95%
  of screening contexts by a decision stump on any single factor.

**GO requires G1, G3 and G4.** G2 is diagnostic: failing it does not stop the
study, it establishes that in this network the three criteria are largely
aligned, which is reported as a finding and removes any basis for admitting a
standalone eco-routing policy.

If G1, G3 or G4 fails, the main campaign is not run and the study reports a
negative result about portfolio design.

## 7. Mechanistic descriptors and rule — FROZEN

Dimensionless, computable before policy activation, from the context alone.
Capacities are the **measured** values of section 10, not textbook constants.

| | Descriptor | Definition |
|---|---|---|
| x1 | network saturation | `D / (cap_C + cap_N + cap_S)` |
| x2 | shortest-corridor saturation | `D / cap_C` |
| x3 | alternative capacity share | `cap_N / (cap_C + cap_N + cap_S)` |
| x4 | effective green ratio | `(g/C * 90 - 4) / 90` |
| x5 | penetration | `p` |
| x6 | information staleness | `lag / T_freeflow,C` |
| x7 | incident regime | indicator that a disruption *may* occur (never its realisation) |
| x8 | controlled-flow saturation | `p * D / cap_C` |

A route-overlap index is not used: the three corridors share only the access
and egress edges, so overlap is structurally constant and carries no
information.

`cap_C = 2 * 1761 * g_eff`, `cap_N = n_alt * 1596 * g_eff`, `cap_S = 1500`.

**Mechanistic rule B1**: an axis-aligned region rule on x1-x8, fitted as a
decision tree of depth <= 2 restricted to these descriptors, trained on
training folds only. Thresholds are reported as **brackets between adjacent
sampled levels**, never as exact continuous values.

## 8. Baseline ladder and evaluation — FROZEN

| | Baseline |
|---|---|
| B0 | best fixed policy (SBS), chosen within training folds only |
| B1 | mechanistic rule (section 7) |
| B2 | decision tree, depth <= 3, on the same descriptors |
| B3 | multinomial logistic regression on standardised descriptors |
| B4 | GBDT advantage selector |
| B5 | B4 + support gate + confidence gate + abstention to B0 |
| ref | VBS, cross-fitted hindsight best policy |

**VBS is retrospective and not deployable.** It is an upper reference, never a
method. SBS is the deployable fixed-policy baseline.

**Primary scientific comparison: B4 vs B1.** Secondary: B4 vs B0, B5 vs B4,
B5 vs B0. It is accepted in advance that B1 may beat B4; if it does, the
finding is that the decision structure is simple enough that a learner adds
nothing, and that is what will be reported.

**B4 target.** For each policy `a`, `Delta_a(x) = C_SBS(x) - C_a(x)`, with SBS
determined on **training contexts only**. Selection picks `argmax_a Delta_hat_a`.

**Model, frozen, not tuned on any test fold**: LightGBM regression,
`n_estimators=400, learning_rate=0.05, num_leaves=15, min_child_samples=20,
subsample=0.9, subsample_freq=1, colsample_bytree=0.9, reg_lambda=1.0,
random_state=0`.

**Validation**: leave-one-context-out. All preprocessing, normalisation, SBS
identification and threshold fitting are recomputed inside each fold. No seed
of a held-out context appears in training. No realised outcome of a test
context is used as a feature.

## 9. Uncertainty, abstention and distribution shift — FROZEN

**Gate 1, support**: mean distance to the 5 nearest training contexts in
standardised descriptor space; abstain above the 95th percentile of the
training fold's own such distances.

**Gate 2, confidence**: split conformal interval on predicted advantage,
alpha = 0.10, calibration on 30% of the training fold; abstain when the
interval for the best policy overlaps that of the training-fold SBS.

Abstention falls back to B0. **Split conformal guarantees coverage under
exchangeability.** Under covariate shift that assumption fails, so the
conformal gate is calibrated in-distribution and heuristic outside it. It is
the *support* gate, not the conformal gate, that addresses extrapolation, and
neither detects concept shift. This is a stated limitation, not a caveat to be
softened later.

**OOD splits, each reported separately with its shift type:**

| | Split | Shift type |
|---|---|---|
| O1 | hold out D = 4200 | extrapolation, high demand |
| O2 | hold out D = 1200 | extrapolation, low demand |
| O3 | hold out D = 2400 | interpolation control |
| O4 | hold out lag = 300 s | extrapolation |
| O5 | hold out penetration = 0.8 | extrapolation |
| O6 | hold out g/C = 0.65 | extrapolation |
| O7 | train incident-free, test incident | covariate + concept shift |
| O8 | incident on the **bypass** — a location absent from all training data | domain shift |

## 10. What the pre-freeze validation runs changed

Scenario validation ran 384 exploratory runs and the policy tests. It was used
to (i) confirm the network's traffic physics, (ii) *measure* capacity, and
(iii) detect implementation defects. It found four things:

1. **Measured capacity.** Saturation flow 1761 veh/h/lane on the arterial,
   1596 on the slower north street, 1500 veh/h/lane uninterrupted on the
   bypass. Capacity consistency across green ratios is within 2% per corridor.
   The demand levels of section 3 follow from these measurements.
2. **Defect — merge priority.** At an ordinary priority merge the alternative
   corridors must yield to the arterial, so any policy using an alternative was
   charged for junction priority rather than for corridor capacity. The
   destination portal now gives each approach a dedicated lane.
3. **Defect — turn-radius ceiling.** The schematic straight-line node geometry
   made the diverge onto the bypass a 8.05 m/s turn, capping the bypass at
   1088 veh/h. With the ceiling removed the bypass measures 1500 veh/h and the
   signalised corridors are unchanged.
4. **Defect — a deterministic incident is not a risk.** An incident occurring
   at an identical time and place in every replication is a known event, and a
   policy that tracks only the mean handles it as well as one that models
   dispersion. Such a scenario cannot test a reliability-aware policy at all.
   The incident was therefore made stochastic (section 3).

No policy parameter was changed. No factor level was chosen because it made a
policy win. The exploratory winner map produced before these corrections is
superseded by them and is used nowhere.

## 11. Analysis freeze

Decision metrics: context-level regret, mean, median, maximum, distribution,
CVaR90, share of contexts with zero regret, share within tolerance, and the
share of the VBS-SBS gap closed. Physical differences in seconds, kilograms
and vehicle-seconds are reported alongside every normalised figure.

Prediction accuracy, ranking accuracy and decision regret are reported as
three distinct quantities and are never substituted for one another.
