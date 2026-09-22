# Experimental Design — scenario space, network, protocol

**Status: proposal.** Nothing has been run. No factor level below is justified by a V2 result,
because no V2 result exists.

---

## 1. Design variables vs measured outcomes

The brief's rule is correct and is enforced throughout: **congestion is an outcome, not a factor.**
Only quantities an operator could set or observe *before* activating a policy may be design
variables or ML features.

| Design variables (settable / known ex ante) | Measured outcomes (never features) |
|---|---|
| Demand level per OD | Realised degree of saturation |
| OD pattern and path overlap | Link flows, densities, queues |
| Link capacity (lanes) | Travel time, P95, delay |
| Signal green ratio and cycle | Emissions |
| Background traffic intensity | Utilisation, spillback |
| Guidance penetration rate | Herding / oscillation indices |
| Information lag (`Δ`) | Policy winner, regret |
| Incident location, severity, duration, announced/unannounced | — |
| Network topology | — |

A *derived* feature computed only from design variables and static network geometry (e.g. a
degree-of-saturation estimate `demand / declared capacity` on the static path) is admissible. A
feature computed from realised traffic is not.

---

## 2. Factor selection — recommended set

Twelve candidate factors were offered. Taking all twelve is not feasible and not necessary. The
recommendation keeps the factors that (a) have a literature-supported mechanism for changing policy
preference, (b) are observable before activation, and (c) plausibly separate the four policies.

### Include (core, 6 factors)

| Factor | Levels (provisional) | Mechanism it activates | Separates |
|---|---|---|---|
| **Demand / degree of saturation** | 4 | Congests the static path | P1 vs rest |
| **Guidance penetration rate** | 3 (e.g. low / medium / high) | Herding, feedback | **P2 vs P3** |
| **Information lag `Δ`** | 3 | Staleness of the reactive estimate | **P2 vs P1/P3** |
| **Incident state** | none / minor / major × announced / unannounced | Creates variance and non-recurrence | **P4 vs rest**, and P2's non-recurrent failure |
| **Alternative-capacity ratio** | 2–3 | Whether spreading has anywhere to spread to | **P3 vs rest** |
| **Signal green ratio** | 2–3 | Shifts effective corridor capacity | Interacts with all |

### Defer (justified, but not in the first main study)

- **OD pattern / number of OD pairs** — include ≥2 OD pairs in the *network* (Section 3) but do not
  make OD count a varied factor initially; it multiplies the campaign and its mechanism overlaps
  with path overlap.
- **Incident duration** — hold at one value; severity and announcement already span the mechanism.
- **Network topology** — reserve entirely for the OOD generalisation test (Section 6, split G).
  Varying topology inside training and then testing on topology is self-defeating.

### Exclude

- **"Congestion" as a factor** — it is an outcome.
- **Path overlap as an independent factor** — it is a property of the network and OD design, fixed
  by Section 3 rather than varied.

**Rationale for the cut:** the six core factors are exactly those that give each of the four
policies a condition under which it should fail. Any factor that does not map to a named failure
mode in `policies/POLICY_COMPARISON.md` is not carrying its weight.

---

## 3. Network requirements

The network is the single most consequential design choice, because V1's limitations were
network-induced. Requirements:

1. **At least two genuinely parallel alternatives** between a primary OD, with **unequal capacity**.
   Without unequal capacity there is nothing for P3 to balance.
2. **Partial route overlap** — alternatives share some links, so diversion has spillover. Fully
   disjoint alternatives make the problem trivially separable.
3. **≥2 OD pairs** whose routes interact, so guided and background traffic genuinely compete.
4. **Signalised junctions** on the alternatives, so green ratio can shift effective capacity.
5. **Incident-capable links** on more than one alternative, so incident location is a meaningful
   factor rather than a proxy for "the one bad link".
6. **Frozen before Phase 4** and never edited afterwards.

**Recommended family: grid + bypass (family B).** A grid supplies overlap and signal interaction; a
bypass of different capacity supplies the parallel alternative with a genuine capacity asymmetry.
Family C (parallel arterial/corridor) is the natural second topology, reserved for the topology OOD
split. Family A (plain grid) alone risks reproducing V1's symmetry problem.

Use a real network only if it demonstrably contains meaningful parallel alternatives; otherwise a
synthetic benchmark with stated limitations is more defensible than a real network whose realism
cannot be validated.

---

## 4. Replications and the noise floor

V1 used three seeds and the seed noise was large enough that four of twenty-four context winners
were unstable. That is too few for a screen whose entire purpose is to distinguish real differences
from noise.

- **Screen:** ≥10 paired seeds per (context, policy), common random numbers across policies.
- **Main study:** ≥5 paired seeds; the screen's measured noise floor determines whether this is
  enough, and that determination is made in Phase 2, before Phase 4.
- **Common random numbers are mandatory** — demand realisation must be identical across policies
  within a (context, seed) cell, so that policy differences are not confounded with demand draws.

---

## 5. Data splits

Splitting is by **context**, never by vehicle and never by replication. All seeds of a context move
together.

Because the factor space is factorial, prefer **grouped, stratified splits over factor
combinations** rather than leave-one-context-out. V1 used LOCO only because 24 contexts was too few
to split once; with a larger V2 design a genuine held-out test set becomes possible, and should be
used. **Reserve a test set that is touched exactly once.**

---

## 6. OOD splits — reported separately, never aggregated

| Split | Construction | Shift type |
|---|---|---|
| A | Unseen demand level inside the training range | Interpolation |
| B | Demand beyond the training support | Extrapolation |
| C | Unseen congestion pattern at seen factor levels | Covariate / concept shift |
| D | Unseen incident location | Compositional shift |
| E | Unseen signal configuration | Interpolation or shift, depending on final levels — state which |
| F | Unseen OD structure | Route-structure shift |
| G | Unseen topology (second network family) | Domain generalisation |

Split G with a single held-out topology is **weak evidence** for domain generalisation and must be
reported as such. Three topologies would not make it definitive either.

---

## 7. Pre-registration

Before Phase 4 the following are written down and committed: the frozen network; the factor levels;
the policy parameterisations (`w`, `Δ`, `k`, `α`, `λ`); the primary metric; the baseline ladder; the
split definitions; and the analysis plan. Any deviation afterwards is reported as a deviation.
