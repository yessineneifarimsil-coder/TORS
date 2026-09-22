# Decision Framework — what "preferred" means in V2

## Why the V1 layer is retired as a primary method

V1 defined preference by a fixed-reference additive cost with declared weights over travel time and
CO₂. Its own completed evidence showed the layer was inert: sweeping the time weight across
twenty-one values from purely time-oriented to purely emissions-oriented changed **none** of the
twenty-four selector decisions, and moved the hindsight-optimal label in exactly one context. A
decision layer that changes no decision cannot be presented as methodology.

There is also a deeper objection, independent of that result. Normalising seconds by a reference
time and grams by a reference mass and then weighting `0.5 / 0.5` fixes an implicit marginal rate of
substitution between time and emissions. That exchange rate is an economic quantity. Choosing it by
convention, and then reporting winners that depend on it, is not defensible when a monetised
alternative exists.

**Decision: the additive-weight layer is removed from the critical path.** It may appear, at most,
as a sensitivity.

---

## The V2 hierarchy

```
        all policies in a context
                 │
    ┌────────────▼────────────┐
    │ 1. PARETO SCREEN        │   remove policies dominated on
    │    (system TT, P95,     │   every retained criterion
    │     CO₂ if retained)    │
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────┐
    │ 2. PRIMARY OBJECTIVE    │   system-level mean journey time
    │    ranks survivors      │   over ALL traffic (guided + background)
    └────────────┬────────────┘
                 │
    ┌────────────▼────────────┐
    │ 3. PREFERENCE           │   reported ONLY where a genuine
    │    SENSITIVITY          │   multi-criterion conflict survives step 1
    └─────────────────────────┘
```

### Step 1 — Pareto screen

Criteria: system mean journey time; a reliability measure (P95 journey time); CO₂ **only if the V2
network is shown to decouple it from travel time**. A policy dominated on all retained criteria is
removed. This step requires no weights at all.

If the Pareto set is a singleton in almost every context, that is itself a finding — it means the
decision is effectively single-criterion, and the paper should say so rather than manufacture a
multi-criteria framing.

### Step 2 — Primary operational objective

**System-level mean journey time across all traffic.** Three reasons:

- It is the objective a network operator actually acts on.
- It is not weight-dependent.
- It correctly charges a policy for externalities it imposes on background traffic. V1 showed
  guided-cohort gains can coexist with background-cohort losses; a primary metric restricted to the
  guided cohort would hide exactly that.

Report the guided-cohort and background-cohort decompositions alongside it, always.

### Step 3 — Generalised cost, as sensitivity only

Where a scalar is needed:

```
GC = VOT · E[T]  +  VOR · SD[T]  +  p_CO2 · E[CO2]
```

**All three parameters must come from published sources and none is supplied here.** Sourcing them
is a Phase 0 deliverable (`literature/LITERATURE_MAP.md`, "to be sourced" table). Reporting a
generalised cost with invented parameters would be worse than reporting no generalised cost.

Report a **sensitivity range**, not a point value: the conclusion must be stated as "the ranking is
stable for VOT in [a, b]" or "the ranking flips at VOR/VOT ≈ c".

Note the useful coupling: if `λ` in policy P4 is set from the same published VOR/VOT ratio, then P4
optimises a quantity consistent with the evaluation metric — which is a coherent design, and should
be stated as a deliberate choice rather than a coincidence.

---

## Explicitly excluded

TOPSIS, VIKOR, PROMETHEE, AHP and fuzzy variants are excluded unless a specific scientific
requirement emerges that the hierarchy above cannot meet. Applying several MCDM methods to nearly
collinear criteria produces agreement by construction and misrepresents methodological concordance
as validation. V1 already demonstrated this: additive and VIKOR first ranks agreed 24/24 on criteria
correlated at ρ = 0.982, which established nothing.

**MCDM is not the novelty of this study and must not be presented as such.**

---

## Regret and benchmarks — carried over from V1 unchanged

These definitions were audited in V1 and remain correct:

```
C*(s) = min_a C(a,s)                      best observed policy in context s
R_s(π) = C(s, π(s)) − C*(s)               regret of rule π in context s
π_HB(s) = argmin_a C(a,s)                 hindsight best-policy benchmark (VBS analogue)
H̄ = mean_s [ C(s, a_fixed) − C*(s) ]      available headroom vs a fixed policy
```

The hindsight benchmark is **retrospective and not deployable**. It is an upper bound on what any
selector could achieve on the benchmark. It is not an algorithm, not a routing method and not an
MCDM method. In V2 it must additionally be **cross-fitted** so that the reference is not computed on
the same data used to fit the selector.

The single-best-solver (SBS) baseline must be determined from **training folds only**.
