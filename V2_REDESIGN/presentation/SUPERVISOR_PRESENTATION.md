# Supervisor Presentation — speaking script

10 slides. Audience: PhD supervisor in transportation / OR. One pass, oral delivery.
**Everything about V2 is a proposal or a hypothesis. Nothing here is a V2 result.**

---

## Slide 1 — Context-Dependent Selection of Urban Routing Policies

A navigation or traffic operator picks one routing strategy for an operating episode. Different
strategies optimise different objectives, so they fail under different traffic conditions.

> **Can we determine, before deployment, which routing policy is appropriate for the current
> traffic context?**

*Visual:* traffic context → choose policy → route assignment → network outcome.

*Say:* "The decision is which strategy to switch on, not which road to send a car down."

---

## Slide 2 — Why we need a stronger policy-selection problem

Three limitations of the current formulation:

1. **Weak policy complementarity** — the policies largely shared one failure mode, so the winner map
   reduced to demand.
2. **Highly correlated decision criteria** — travel time and CO₂ moved together, so the
   multi-criteria layer changed no decision.
3. **The adaptive model was close to a simple demand rule** — a single split captured most of the
   available decision value.

> The redesigned study will **first test whether meaningful policy complementarity exists**.

*Say:* "V1 answered its question honestly, and the answer was narrow. V2 has to make the decision
problem real before it builds a better model for it."

---

## Slide 3 — Policy selection vs route selection

```
LEVEL 1   context  ──►  routing policy      ← the model learns this
LEVEL 2   policy   ──►  individual routes   ← the policy's own objective
```

Provisional portfolio: **SP** · **DTT** · **capacity-aware load balancing** · **reliability-aware**.

*Say:* "This is per-instance algorithm selection applied to route guidance. The simulator is the
performance oracle. It is not route prediction, not signal control, not reinforcement learning."

---

## Slide 4 — Different policies have different failure modes

| Policy | Main strength | Main weakness | Triggering condition |
|---|---|---|---|
| Static / shortest | simple, efficient | overloads its own preferred route | demand approaches shortest-corridor capacity |
| Reactive DTT | responds to congestion | information lag, **herding**, oscillation | high penetration; lag long vs trip time; abrupt events |
| Capacity-aware | balances load | spreads traffic that needed no spreading | light demand; one dominant path |
| Reliability-aware | avoids variable routes | pays a detour premium when stable | stable conditions; noisy variance estimate |

*Say:* "This is the slide that matters. A portfolio is only selectable if its members fail for
**different reasons**. V1's did not."

---

## Slide 5 — Traffic context: what can change policy preference?

**Design variables** (settable / known before activation): demand · penetration · information lag ·
incident location and severity · alternative-capacity ratio · signal green ratio.

**Measured outcomes** (never features): realised saturation · flows and queues · travel time and P95
· emissions · utilisation.

> **Congestion is an outcome, not a factor.**

*Say:* "Penetration and incidents are the two V1 could not vary. Without penetration there is no
herding; without incidents there is no variance — so two of the four policies would have nothing to
be good at."

---

## Slide 6 — Decision framework: avoiding arbitrary weights

The additive 0.5/0.5 weighting is **removed as the primary method**. New hierarchy:

1. **Pareto screening** — remove dominated policies, no weights needed.
2. **System-level mean journey time** over all traffic — ranks the survivors.
3. **Preference sensitivity** — reported only where a genuine conflict survives step 1.

If a scalar is required: generalised cost from **published** VOT / VOR / carbon values, with a
sensitivity range.

> **We do not invent weights merely to create a winner.**

*Say:* "The system-level objective also charges a policy for what it does to background traffic —
V1 showed guided-cohort gains can coexist with network-level losses."

---

## Slide 7 — Mechanism-informed ML for policy selection

```
context → mechanistic features → GBDT advantage model
        → per-policy predicted advantage → ranking → recommended policy
```

The model predicts **advantage relative to a baseline**, Δ_a(x) = C_SBS(x) − C_a(x), not raw travel
time. That centres the target on zero at the decision boundary and removes the large common mode.

*Say:* "Strong tabular ML, not a deep model. Low-dimensional, interaction-heavy, a few thousand
context-level instances — that is the regime where boosted trees are the right default. A graph
network would be sophistication without a matching problem structure."

---

## Slide 8 — When should we trust the selector?

```
new context → support gate → confidence gate → ACT  or  ABSTAIN → fixed policy
```

Shift types tested **separately**: interpolation · extrapolation · unseen incident · unseen OD ·
unseen topology.

> **The selector is allowed to say: I do not know.**

*Say:* "This is not fashion. In V1, holding out a whole demand level made the selector *worse than
the fixed policy it replaced* — it extrapolated confidently and could not decline. One caveat I want
on the record: conformal prediction guarantees coverage only under exchangeability, so it is a
calibrated gate in-distribution and a heuristic outside it. The **support** gate is what handles
extrapolation."

---

## Slide 9 — Evaluation: does ML really add decision value?

```
best fixed  →  mechanistic rule  →  standard ML  →  GBDT  →  selective GBDT
                                                    reference: hindsight VBS (not deployable)
```

Primary metrics: regret · closed VBS−SBS gap · CVaR₉₀ regret · OOD risk · non-inferiority.

> **Critical test: does the model beat the strong mechanistic rule?**

*Say:* "Beating the best fixed policy is too low a bar — V1 did that with one split. If the
mechanistic rule wins, the finding is that the decision is mechanistically simple, and we report
that."

---

## Slide 10 — What we expect to learn

**Hypotheses, not results:**

1. Routing policies will show complementary strengths across operating regimes.
2. The strongest policy will depend on traffic, network **and information** conditions, not demand
   alone.
3. A mechanism-informed selector will capture useful structure.
4. Uncertainty and abstention will reduce harmful decisions under shift.
5. The study will identify when adaptive selection is genuinely useful and when a fixed strategy
   suffices.

> We aim to characterise the operating regions of established routing policies and develop a
> context-aware, uncertainty-aware method for selecting among them.

**Decision required: portfolio · scenario factors · decision objective · ML architecture.**
