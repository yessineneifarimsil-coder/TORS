# V2 Methodology Proposal

## 0. Two things to settle before reading further

**The methodological audit referred to in the brief was not attached to this session.** This
proposal is therefore built from (a) my own analysis of the completed V1 study and (b) the
literature actually retrieved and verified during this project. Where the brief asserts an audit
finding I could not independently check, I say so. If the audit document exists, it should be
placed in `literature/` and this proposal reconciled against it.

**No V1 simulation assets exist in this project.** The V1 network, route and configuration files
were never supplied — only the compiled manuscript, figures and the analysis workbook. V2 therefore
builds its simulation environment from scratch. This is not a loss: Section 7 of the brief requires
a new network anyway, and a clean build removes any temptation to compare V2 numbers against V1
numbers produced in a different environment. **V1 and V2 results must never be pooled.**

What *is* reusable is the V1 decision-analysis machinery — regret, headroom, hindsight benchmark,
leave-one-context-out protocol, hyperparameter/seed/weight robustness battery. That code is
correct, audited, and directly generalises. It is the main asset carried forward.

---

## A. Executive methodological recommendation

V1 answered its question honestly and the answer was narrow: in a single synthetic mesh with one
OD pair and two near-collinear criteria, routing-policy preference is essentially a function of
demand, and a one-split rule captures most of the available decision value. That is a real finding,
but it is a finding about *that environment*, and it does not establish that policy selection is a
substantive decision problem.

The redesign should therefore not begin by building better machine learning. It should begin by
establishing, experimentally, that the decision problem exists. Concretely:

1. **Make complementarity a hypothesis under test, not a design assumption.** Run a small screening
   experiment first. If the candidate policies do not separate, report that and stop — do not tune
   the network until they do.
2. **Replace the portfolio on the basis of *failure modes*, not objectives.** V1's three policies
   shared one failure mode (they all degrade when the shortest corridor congests). A portfolio whose
   members fail under *different* mechanisms is the only kind that can generate complementarity.
3. **Add the two factors V1 structurally could not vary: guidance penetration and disruption.**
   Without penetration there is no herding, so reactive routing cannot fail in the way the
   literature says it fails. Without disruption there is no travel-time variance, so a
   reliability-aware policy has nothing to be good at. These two factors are not enrichment; they
   are what make P2 and P4 distinguishable at all.
4. **Design the network so the alternatives differ in capacity.** V1's parallel corridors differed
   in speed and lanes but shared a single dominant OD, so the decision collapsed to "use the short
   one or don't". Genuine parallel alternatives of *unequal capacity* with *partial overlap* are the
   minimum structure for a load-balancing policy to matter.
5. **Retire the additive-weight decision layer as the primary method.** Report a system-level
   operational objective, screen with Pareto dominance, and use monetised generalised cost only as a
   sensitivity with published parameters. V1 already demonstrated that the weights changed no
   decision; continuing to present them as methodology would be indefensible.
6. **Keep the ML proportionate and targeted at the decision.** Predict policy *advantage* relative
   to a training-fold baseline, not raw outcomes. Add uncertainty and abstention because the V1
   extrapolation result showed a selector that cannot say "I don't know" is actively harmful outside
   its support. That is the strongest single justification for the uncertainty component, and it
   comes from our own completed evidence.

**The honest risk, stated up front.** It is entirely possible that the redesigned study also finds
that a two- or three-variable mechanistic rule captures most of the decision value. The design must
be able to report that cleanly, which is why baseline B1 (mechanistic rule) is mandatory and why the
headline test is "does the ML beat the rule", not "does the ML beat the best fixed policy".

---

## B. Primary research question

> Across demand, congestion, information, signal, penetration and disruption conditions, under what
> operating contexts do established route-guidance policies exhibit complementary strengths, and can
> those context-dependent differences be identified before deployment?

**RQ2.** Can a context-aware ML selector outperform a strong mechanistic selection rule and the best
fixed policy?

**RQ3.** How do uncertainty and distribution shift affect policy-selection reliability?

**RQ4.** Under what conditions should the learned selector abstain and fall back to a fixed policy?

No claim is made in advance that adaptation is beneficial. RQ2 is genuinely two-sided.

---

## C. The decision problem, stated precisely

Two levels, never conflated:

```
LEVEL 1   context x  ──►  choose ONE routing policy a ∈ A          ← this is what is learned
LEVEL 2   policy a   ──►  assigns routes to guided vehicles        ← the policy's own objective
```

This is **per-instance algorithm selection** (Rice's formulation) applied to route-guidance
policies, with a traffic simulation as the performance oracle. It is not route prediction, not
signal control, not multi-agent RL, not a contextual bandit — there is no sequential exploration
and no per-vehicle action.

The instance is the **operating context** (a scenario configuration), not a vehicle and not a
replication. All replications of a context move together through every split. This was already
enforced in V1 and carries over unchanged.

---

## D. What changes from V1, and why each change is necessary

| V1 | V2 | Why |
|---|---|---|
| 3 policies sharing one failure mode | 4 policies with distinct failure modes | Complementarity requires distinct failure mechanisms, not distinct objectives |
| 1 OD pair, one dominant corridor | multiple OD pairs, partial overlap, unequal-capacity alternatives | Load-balancing has no meaning without parallel capacity to balance |
| demand × restriction × signal | adds penetration, information lag, incident state | Herding and variance cannot arise otherwise |
| speed restriction only | stochastic incidents (location, severity, duration, announcement) | Creates the variance that reliability-aware routing targets |
| additive weights as primary decision | Pareto screen + system objective; generalised cost as sensitivity | V1 showed weights changed no decision |
| depth-3 CART on raw outcomes | GBDT on policy advantage, mechanistic dimensionless features | Targets the decision quantity directly |
| no uncertainty handling | support gate + conformal confidence gate + abstention | V1 showed unguarded extrapolation is worse than not adapting |
| one OOD test (hold out a demand level) | seven separately reported shift types | A single number conflates distinct failure modes |

---

## E. Phase plan and gates

| Phase | Output | Gate to proceed |
|---|---|---|
| 0 | Literature table; exact policy specifications; sourced VOT/VOR/carbon values | Every policy has a primary-literature formulation |
| 1 | Policy implementations + known-answer unit tests | Each policy reproduces its objective on a hand-checkable network |
| 2 | **Complementarity screen** | **≥3 policies win ≥1 context each beyond the seed noise floor, and ≥1 non-trivial Pareto set exists** |
| 3 | Frozen scenario space, frozen network, pre-registered analysis | Written and committed before Phase 4 |
| 4 | Main SUMO dataset | All runs complete; no post-hoc network edits |
| 5 | ML trained on training contexts only | Leakage audit passes |
| 6 | Held-out + seven OOD evaluations | Test data touched exactly once |
| 7 | Statistical analysis at context level | — |
| 8 | Interpretation and write-up | — |

**Phase 2 is a stop/go gate.** If it fails, the deliverable is a negative result on portfolio
design, not a retuned network.

---

## F. What must not happen

- No network geometry change after seeing which policy wins.
- No weight chosen because it produces an interesting ranking.
- No V1 number reused, restated, or reconciled as if it were V2 evidence.
- No realized outcome used as an ML feature.
- No vehicle treated as an independent instance.
- No claim that the hindsight benchmark is deployable.
- No sophisticated model adopted without demonstrating it beats the mechanistic rule.
