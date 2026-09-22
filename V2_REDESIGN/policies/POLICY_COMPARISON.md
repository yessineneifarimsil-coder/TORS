# Policy Portfolio — specification and comparison

**Status: provisional.** Nothing here is final until Phase 0 (literature) and Phase 1
(implementation validation) are complete. Expected strengths and weaknesses are **hypotheses**, not
results.

## Design principle

A portfolio is useful for selection only if its members **fail under different mechanisms**. V1's
portfolio failed this test: SP, DTT and TECO10 all degrade when the shortest corridor congests, so
their ordering reduced to a single congestion variable. The four policies below are chosen so that
each has a distinct, nameable failure mode.

---

## Comparison table

| | Objective | Information used | Hypothesised strength | Hypothesised failure mode | Triggering condition for failure |
|---|---|---|---|---|---|
| **P1 Static / shortest** | `min_p L(p)` (distance or free-flow time) | none | Light demand; stable conditions; when a detour cannot repay its length | Overloads its own preferred route | Demand approaches the capacity of the shortest corridor |
| **P2 Reactive dynamic travel time** | `min_p T̂_p(t)` from an observation window of length `w`, refreshed every `Δ` | lagged link travel times | Recurrent, slowly varying congestion | Information lag; **herding**; oscillation between corridors | High guidance penetration; lag large relative to free-flow trip time; abrupt (non-recurrent) events |
| **P3 Capacity-aware load balancing** | spread guided demand across acceptable paths, weighted by residual capacity (see below) | link flows/occupancy + capacity estimate | Near-capacity operation; high penetration; genuine parallel alternatives | Spreads traffic that did not need spreading; sensitive to capacity mis-estimation | Light demand; one dominant path; poor capacity estimates |
| **P4 Reliability-aware** | `min_p [ μ̂_p + λ σ̂_p ]` or a percentile equivalent | mean **and** dispersion of link/route travel time | Disruption-prone, high-variance conditions | Pays a detour premium when conditions are actually stable; variance estimate is noisy on short windows | Stable conditions; short observation windows; few replications |

Every row is an **established policy family**. None is presented as a new algorithm.

---

## P1 — Static / shortest routing

Zero-information reference. Shortest path on a fixed weight (distance, or free-flow travel time —
choose one and state it). Deterministic within a context.

Purpose: it is the control. Any claim that guidance helps is measured against this.

---

## P2 — Reactive dynamic travel time

`min_p Σ_{e∈p} t̂_e(k)` where `t̂_e(k)` is the mean travel time on link `e` observed over the last
completed interval `k` of length `w`, refreshed every `Δ`.

**Specify and report `w` and `Δ`.** V1 used completed 60 s intervals. Information lag becomes an
experimental factor in V2, so `Δ` is no longer a fixed implementation detail.

**Do not describe P2 as predictive.** It uses lagged observations. If a forecasting variant is
wanted, that is P5 and it must contain an actual forecast model.

---

## P3 — Capacity-aware load balancing — **formulation correction**

The brief proposes

```
min_x max_e ρ_e(x)   s.t.  Σ_p x_p = 1,  x_p ≥ 0,  T̂_p ≤ (1+α) T̂_min
```

**This is a flow-assignment program over a path distribution, not a per-vehicle routing policy**,
and SUMO routes individual vehicles. Adopting it as written would require solving a min-max program
per decision epoch and then sampling vehicles from `x*`, which (i) has no clean precedent as a
*deployed guidance policy*, (ii) adds a solver dependency, and (iii) makes P3 a different *kind* of
object from P1/P2/P4, weakening the comparison.

**Recommended instead: the load-balancing k-shortest-path family**, for which there is direct and
citable precedent. Pan et al. (2013) define exactly this class of proactive rerouting strategies —
random k-shortest-path, entropy-balanced k-shortest-path (EBkSP) and flow-balanced k-shortest-path
(FBkSP) — as deployable per-vehicle guidance that spreads load across alternatives rather than
collapsing onto one. Related load-aware detour formulations appear in Chen et al. (2025) and in the
dynamic-vehicle-selection rerouting line (Tseng et al. 2021; Ho et al. 2023; Tay et al. 2025).

Proposed concrete form for V2:

1. Generate the k shortest acceptable paths for the OD, filtered by `T̂_p ≤ (1+α) T̂_min`.
2. Assign each guided vehicle to the acceptable path with the greatest residual capacity share,
   where the residual is computed from current link occupancy against a declared capacity.
3. `k` and `α` are declared parameters, frozen before Phase 4.

This keeps the *intent* the brief specifies (avoid overloading the same shortest route, respect a
travel-time acceptability constraint) while remaining a per-vehicle policy with published
precedent. **The exact variant must be fixed in Phase 0 against the primary sources**, and a
known-answer unit test must show that on a two-path network with unequal capacity the policy splits
in the intended direction.

---

## P4 — Reliability-aware routing

`min_p [ μ̂_p + λ σ̂_p ]`.

Two implementation risks that must be resolved in Phase 0, not discovered in Phase 4:

- **Where does `σ̂` come from?** Within-run dispersion across vehicles traversing a link in the
  observation window, or across-replication dispersion? Only the first is available to a *deployed*
  policy, so it is the defensible choice — but it is noisy on short windows, and that noise is
  itself part of P4's failure mode. State the estimator explicitly.
- **Where does `λ` come from?** Not from convenience. Tie it to a published reliability ratio
  (value of reliability ÷ value of time) so that `μ + λσ` is a monetised generalised cost rather
  than an arbitrary scalarisation. This also makes P4 consistent with the decision framework in
  `methodology/DECISION_FRAMEWORK.md`. **The numeric value must be sourced in Phase 0 and reported
  with a sensitivity range.**

A percentile form (`min_p T̂_p^{95}`) is an acceptable alternative if the dispersion estimate proves
too unstable; decide in Phase 1 on the basis of the unit tests, not on the basis of results.

---

## Conditional and excluded policies

**Eco-routing is excluded from the core portfolio.** V1 established, on its own completed evidence,
that in that environment travel time and CO₂ correlated at ρ = 0.982 and the emission-oriented
policy was outcome-identical to shortest-path routing in 21 of 24 contexts. Re-including eco-routing
is justified only if the V2 network is shown to produce genuine time–CO₂ decoupling — which is an
empirical question about the new network, testable in the screen. Until then it is future work.

**P5 Predictive DTT** is admissible only if information lag is retained as a central factor *and* an
actual forecasting model is implemented. Do not add it to make the portfolio look larger.

**Hard cap: 5 policies.** Every added policy multiplies the simulation campaign and dilutes the
per-policy statistical power in the screen.

---

## What would falsify this portfolio design

If the screen shows that P1/P2/P3/P4 orderings are explained by a single congestion variable — i.e.
that the winner map is again one-dimensional — then the portfolio has failed on the same grounds as
V1's, and the correct response is to report that, not to add a fifth policy or retune the network.
