# Reviewer Attack List

The strongest objections a referee can raise, and where the manuscript answers
each. Objections are stated in the form a hostile referee would use, not in a
form convenient to answer. Where the honest answer is "this is a real
limitation", that is what appears.

---

### A1. "This is a synthetic network. Nothing here transfers to a real city."

**Where answered:** Limitations; Section 5 (network).
**Answer.** Correct, and the paper claims no external validity. The environment
is a controlled instrument for isolating mechanisms, not a model of anywhere.
Every claim is scoped to it. What does transfer is the *method*: the
descriptors are dimensionless, so the boundary is stated in terms of degree of
saturation and controlled-flow share rather than in vehicles per hour, and the
same quantities are measurable on a real network. No claim of real-world
validation is made anywhere in the paper.

### A2. "You tuned the network until the policies separated."

**Where answered:** Section 5; `spec/FROZEN_SPEC.md` §10; commit history.
**Answer.** The specification was written and committed before any evaluation
run. Three network changes were made, all before the freeze and all on
mechanism grounds, and all three are recorded with their reasons: a
conflict-free destination merge (an ordinary priority merge charged the
alternative corridors for junction priority rather than capacity), removal of a
turn-radius speed ceiling that capped the bypass at a value belonging to the
schematic drawing rather than the road, and a stochastic rather than
deterministic incident. No policy parameter was ever changed. No factor level
was chosen because it made a policy win; the demand levels follow from the
*measured* capacity. The git history timestamps the freeze before the data.

### A3. "The screening gate failed and you carried on anyway."

**Where answered:** `results/SCREENING_REPORT.md` (deviation D-1); Results.
**Answer.** Yes, and it is recorded as a deviation rather than dissolved by
reinterpretation. The reasons are stated, were known at the time of the
decision, and none is a result the campaign might produce: a selection problem
demonstrably exists (the preferred policy reverses with resolved margins up to
18%); the gate was written against one criterion and is blind to the
three-criterion structure beside it, in which all four policies are
non-dominated somewhere; and the negative finding itself rested on 16 of 648
contexts sampled at extreme levels only, never touching the demand transition
region. The main campaign was run to substantiate the negative result, and a
confirmatory gate on the full data was declared before it was launched and is
reported whatever it says.

### A4. "Your headroom is small, so the whole exercise is pointless."

**Where answered:** Results; Discussion.
**Answer.** If the headroom is small, that *is* the finding, and it is reported
with its physical magnitude in seconds rather than as a normalised percentage
that would flatter it. A study that only reports large effects is not a study.
The operational conclusion --- that fixed-policy operation is adequate over a
stated region and inadequate over another --- is useful precisely because the
region where adaptation pays is bounded and identified.

### A5. "GBDT beating a fixed policy is trivial. Any model would."

**Where answered:** Section 7; Table 5; Discussion.
**Answer.** Agreed, which is why the primary comparison is **not** against the
fixed policy. It is against the mechanistic rule B1, a depth-2 axis-aligned
rule on physically interpretable descriptors. The ladder also includes a depth-3
tree and a multinomial logistic model. If the learner does not beat the
mechanistic rule, the paper says so and concludes that the decision structure is
simple.

### A6. "Conformal prediction does not give you out-of-distribution guarantees."

**Where answered:** Section 7; Limitations.
**Answer.** Correct, and the paper states it rather than glossing it. Split
conformal coverage holds under exchangeability, which covariate shift breaks.
The conformal gate is a calibrated instrument in-distribution and a heuristic
outside it; the *support* gate is what addresses extrapolation; and neither
detects concept shift. No coverage claim is made on any out-of-distribution
split.

### A7. "The demand is known to the selector. Real operators must forecast it."

**Where answered:** Limitations.
**Answer.** True and material. The study assumes the context is observable at
decision time and does not address forecasting it. A deployed system would
inherit the forecast's error on top of the selector's. This is stated as a
limitation and is not worked around.

### A8. "Five seeds is not enough."

**Where answered:** Section 5; the resolution criterion.
**Answer.** The design does not rely on seed count alone. Comparisons are
paired under common random numbers, which removes the dominant variance
component, and no difference is claimed unless the paired seed difference
exceeds twice its standard error. Differences that the seeds cannot separate
are reported as ties, and the share of such ties is itself reported rather than
hidden. The screening subset used ten seeds and its unresolved margins were
median 0.13%, indicating that the unresolved cases are genuinely near-ties.

### A9. "P4 is just P2 with an extra term. The portfolio is padded."

**Where answered:** Results (complementarity); Discussion.
**Answer.** This is tested rather than asserted. Pairwise outcome-identity is
reported for all six policy pairs, and P2/P4 is the highest of them. Where they
differ, the difference is quantified. If P4 turns out to be redundant on the
primary criterion, that is reported as a finding about reliability-aware routing
in this environment --- including the case where it is nonetheless the most
frequently non-dominated policy because it minimises stopped delay.

### A10. "Why no eco-routing policy, when you measure \CO{}?"

**Where answered:** Section 2; Results (criterion audit).
**Answer.** Because the evidence does not support adding one. The
time/\CO{} correlation and the frequency with which the two criteria rank
policies identically are measured and reported. An objective that is nearly
monotone in travel time adds a label, not a policy. The exclusion is an
empirical result, and the numbers supporting it are given so a referee can
disagree with the threshold rather than with an assertion.

### A11. "Insertion delay inflates your journey times."

**Where answered:** Table 3; Section 4.
**Answer.** Deliberately. A policy that oversaturates the network produces
vehicles that cannot enter it. Excluding their wait would credit a policy for
the queue it caused. In-network time is reported separately as a diagnostic, so
the decomposition is visible.

### A12. "System-wide averages hide what happens to the guided vehicles."

**Where answered:** Section 4; Results.
**Answer.** All three criteria are reported at three cohort levels: system-wide
(primary), the corridor cohort, and the guided cohort. The primary objective is
system-wide precisely so that a policy cannot be rewarded for helping guided
vehicles at the expense of background traffic --- the opposite of the objection's
concern, and the reason the choice was made.

### A13. "Your capacity numbers are SUMO artefacts, not traffic engineering."

**Where answered:** Section 5; `tests/test_capacity.py`.
**Answer.** They are measured in this environment and reported as such, not
imported from a handbook. The measurement is internally consistent: one
saturation flow explains every green ratio within 2% per corridor, capacity
scales with lane count, and the two signalised corridors differ in the
direction their speed limits require. The uninterrupted bypass carries less
than queue-discharge saturation flow, as free-flow headways require. These are
the checks a traffic engineer would run, and they are in the repository.

### A14. "Contributions 1-4 are just a pipeline. Where is the novelty?"

**Where answered:** Section 1; Section 2 (positioning).
**Answer.** The paper explicitly claims no new routing algorithm, no new
learning algorithm and no new decision method, and says so in the introduction.
Every component is cited to prior work. What is offered is the integration and
the empirical characterisation, and the positioning paragraph states the
narrow combination being claimed rather than asserting that no one has studied
regime-dependent routing.

### A15. "One origin-destination pair is not a network."

**Where answered:** Limitations.
**Answer.** Fair. The corridor demand is a single OD pair; the four minor
streets carry independent demand through the same signals, which is what
couples the routing decision to traffic that is not being routed, but the
routing choice itself is a three-way choice on one OD pair. Generalising to
many simultaneously-routed OD pairs is the clearest next step and is named as
such rather than implied to be covered.
