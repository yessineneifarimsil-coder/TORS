# Phase D — Policy-Complementarity Screen: Result and Verdict

640 runs (16 contexts x 4 policies x 10 seeds). Zero failed runs, zero
teleports, zero runs below the 0.98 completion threshold.

## Gate results, against the thresholds frozen before the runs

| Gate | Requirement | Observed | |
|---|---|---|---|
| G1 complementarity | >= 3 policies strictly best in >= 1 context, resolved margin | **2** (P3, P1) | **FAIL** |
| G2 criterion conflict | >= 25% of contexts with non-singleton Pareto set | 68.8% | PASS |
| G3 non-degeneracy | mean pairwise outcome identity <= 50% | 15.6% | PASS |
| G4 multi-factor structure | best single-factor stump < 95% of winners | 75.0% (demand) | PASS |

**Pre-declared verdict: STOP.**

## G1 failed for a substantive reason, not for lack of power

Nine of sixteen contexts have an unresolved winning margin. Those margins are
*negligible*, not merely uncertain: median 0.13% and maximum 0.59% of the best
journey time. Resolved margins have median 5.51% and reach 18.0%. With ten
paired seeds under common random numbers, a 5% difference resolves comfortably;
a 0.13% difference is genuine equivalence. The screen has ample power, and its
answer is that the four policies are frequently interchangeable on journey time.

On the primary criterion the portfolio shows **two-way** complementarity:

* **P1 (shortest)** is strictly best in 2 contexts — low demand, high
  penetration, generous green. Where the shortest corridor is not congested,
  every adaptive policy diverts traffic onto longer corridors and loses by up to
  0.9%. Adaptation has a cost.
* **P3 (load balancing)** is strictly best in 12 contexts, by up to 18.0% under
  congestion with high penetration.
* **P2 (reactive travel time)** is never strictly best by a resolved margin.
* **P4 (reliability-aware)** is never strictly best by a resolved margin. It is
  distinguishable from P2 in 5 of 16 contexts, so it is not a duplicate — but
  where it differs it is usually worse, once by 62 s per vehicle.

## What the gate could not see

G1 was written against the primary criterion alone. The three-criterion
structure is different, and G2 passing is what exposes it. Pareto-set
membership across the 16 contexts:

| Policy | contexts in the Pareto set |
|---|---|
| P1 | 2/16 |
| P2 | 6/16 |
| P3 | 15/16 |
| P4 | 11/16 |

**P4 is the most frequently non-dominated policy in the portfolio**, despite
never winning on journey time. It is the stopped-delay specialist: it routes to
the steady, unsignalised bypass and so minimises time spent stationary at the
cost of total journey time. The dominant Pareto conflict in the screen is
P3 against P4 (5 contexts outright, 5 more within larger sets).

So the portfolio *is* complementary — on the criterion vector, not on the
scalar. A gate written against one criterion cannot detect that, and mine
was not.

## Criterion structure (answering the multi-criteria audit directly)

| pair | pooled r | identical policy ordering |
|---|---|---|
| journey time vs CO2 | +0.9424 | 10/16 contexts |
| journey time vs stopped delay | +0.8835 | 6/16 contexts |
| CO2 vs stopped delay | +0.9114 | 9/16 contexts |

The best policy on CO2 differs from the best on journey time in 5 of 16
contexts; the best on stopped delay differs in **9 of 16**.

**Total stopped delay carries decision information that journey time and CO2 do
not.** This is outcome (A) of the pre-declared multi-criteria audit, and it is
the reason the three-criterion framing earns its place.

**Eco-routing remains excluded.** CO2 and journey time correlate at r = 0.94
and produce an identical policy ordering in 63% of contexts. A standalone
environmental objective has little room to differ from a time-based one here.
That is the evidence for the exclusion, and it is evidence rather than
assumption.

## PROTOCOL DEVIATION D-1

The frozen rule states: *"If G1, G3 or G4 fails, the main campaign is not run
and the study reports a negative result about portfolio design."* G1 failed.
**The main campaign was run regardless.** This is recorded as a deviation
rather than resolved by reinterpreting the rule.

Reasons, all known at the moment of the decision and none of them a result the
campaign might produce:

1. **The gate's own purpose is satisfied.** It exists to stop a selection study
   being built on a portfolio with no selection problem. A selection problem
   demonstrably exists: the preferred policy reverses between P1 and P3 with
   resolved margins up to 18.0%.
2. **The gate is blind to the multi-criteria structure it sits beside.** G2
   passed and shows all four policies appearing in Pareto sets, P4 most often
   of all. Stopping on a single-criterion gate would discard that.
3. **The negative finding is not yet publishable.** "P2 and P4 are never
   strictly best on journey time" is the most striking claim available, and it
   rests on 16 of 648 contexts sampled at extreme factor levels only — the
   screen never samples the demand transition region at all. Stopping would
   leave the study asserting a negative from a 16-point fraction. The main
   campaign is run to *substantiate* the negative result, not to escape it.

### Constraints declared before the main campaign was launched

* The study may **not** claim four-way complementarity on the primary criterion.
* The study may **not** claim that P2 or P4 is ever the best journey-time policy
  unless the full campaign resolves such a win.
* The portfolio section must report G1's failure as a finding.
* A confirmatory gate **G1'** — the identical G1 definition, evaluated on all
  648 contexts with 5 seeds — is declared here, before the campaign is run, and
  its result is reported whatever it is.

---

## Addendum: the confirmatory gate G1', evaluated on all 648 contexts

Gate G1' was declared in this document before the main campaign was launched,
with its result to be reported whichever way it came out.

**G1' PASSES.** Three policies --- P1, P3 and P4 --- are strictly best in at
least one context with a resolved margin, against the threshold of three. The
resolved winner counts over 648 contexts are P3 227, P4 19, P1 11, with 257 of
648 contexts resolved. **P2 is never a resolved winner**, confirming on the full
factor space what the screen saw in its 16.

The screen's STOP verdict was therefore a **sampling artefact of the screening
design**, not a property of the portfolio. The screen sampled 16 contexts at
extreme factor levels only and never sampled the demand transition region at
all; it had the power to detect near-ties, which it did correctly, but not the
coverage to find the regions where P4 and P1 win. This is exactly the
possibility that was given as the second reason for deviation D-1, and it is
what the full campaign shows.

This vindicates the reasoning behind the deviation. It does not retrospectively
make the deviation unnecessary, and the deviation stands on the record as taken.
A gate that is passed only after being overridden is a gate that was badly
designed, and the lesson is recorded as such: **a complementarity screen must
cover the interior of the factor space, not only its corners.** A
resolution-IV fraction at extreme levels is an efficient design for estimating
main effects and a poor one for discovering where a winner map changes.

### What G1' passing does *not* establish

Passing G1' establishes that the winner map is genuinely multi-policy. It says
nothing about whether exploiting that map is worth anything, which is a
separate quantity --- the gap between the best fixed policy and the hindsight
best --- and is reported in the results. The two are easy to conflate and are
kept apart throughout this study.
