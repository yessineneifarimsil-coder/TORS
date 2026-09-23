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

**Where answered:** `results/SCREENING_REPORT.md` (deviation D-1 and its
addendum); Results 7.2.
**Answer.** Yes, and it is recorded as a deviation rather than dissolved by
reinterpretation. The reasons were stated at the time and none was a result the
campaign might produce. The confirmatory gate G1', declared in the same document
before the campaign was launched, **passed** on all 648 contexts: three policies
are strictly best somewhere by a resolved margin. The screen's STOP was a
sampling artefact of a 16-context resolution-IV design at extreme factor levels
that never sampled the demand transition region.

That vindicates the reasoning but does not retrospectively excuse the deviation,
and the report says so. The design lesson is recorded with it: a complementarity
screen must cover the interior of the factor space, not only its corners.

### A4. "Your headroom is 0.45 s. Why is this publishable?"

**Where answered:** Results 7.3--7.5; Discussion 8.6.
**Answer.** Because the size of the headroom is the result, not an obstacle to
it. Three things make it worth reporting. First, it is measured against a
quantity that is *not* small: choosing the wrong fixed policy costs 46.4% of
system journey time, so the paper separates a decision worth 46% from one worth
0.12% that the literature routinely treats as the same question. Second, the
mechanism is identified and general: the best fixed policy has an upside 18x its
downside, and any portfolio with such a member will show the same pattern.
Third, the diagnostic is cheap and transferable --- compare the best fixed
policy with the retrospective best, and both with the noise floor of the same
comparison, before choosing a model class.

A study that reports only large effects is a study that has decided its
conclusion in advance.

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

**Where answered:** Results 7.2 and 7.9; Table 4.
**Answer.** The data say the opposite, and about a different policy. P4 is
strictly best on journey time in 19 contexts by a resolved margin, is
non-dominated in 81.0% of contexts, and **minimises total stopped delay in 429
of 648 contexts** while minimising journey time in only 129. It is the
stopped-delay specialist, and dropping it would remove the only policy that
optimises that criterion.

The policy that is redundant on journey time is **P2**, which is never a
resolved winner anywhere in the factor space. That is reported as a finding
about reactive travel-time routing in this environment, not hidden.

### A10. "Why no eco-routing policy, when you measure \CO{}?"

**Where answered:** Section 2; Results 7.9.
**Answer.** Because the measured evidence does not support adding one. Across
648 contexts, journey time and \CO{} correlate at r = 0.939 and rank the four
policies identically in 52.2% of contexts; the best policy on \CO{} differs
from the best on journey time in 29.6%. By contrast, stopped delay disagrees in
56.0%. An objective nearly monotone in travel time adds a label rather than a
policy, and the numbers are given so a referee may disagree with the threshold
rather than with an assertion.

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


### A16. "Your safety gate never fires usefully --- B5 just equals B0."

**Where answered:** Results 7.8; Discussion 8.4.
**Answer.** That is the finding, and it is the correct behaviour. The conformal
interval on the predicted advantage is wider than the advantage itself, so a
gate requiring a positive lower bound cannot certify a gain. Loosening it until
it acted would be exactly the failure mode this study is written against.

What the gate buys is bounded and stated: it prevented every out-of-distribution
harm constructed (unseen high demand 0.98 -> 0.00 s; unseen disruption regime
2.22 -> 0.63 s), and it cost the 0.25 s in-distribution gain that the unguarded
selector achieves. Both halves of that trade are reported.

### A17. "Your support gate did not detect the domain shift in O8."

**Where answered:** Results 7.8; Limitations.
**Answer.** Correct, and the paper says so rather than omitting the split. When
the disruption moves to a corridor that carries none in training, the support
gate flags 0% of held-out contexts --- because the incident's *location* is not
among the eight descriptors, so those contexts are genuinely inside the training
support as the feature space defines it. A support gate defined on a feature
space cannot detect a shift that leaves that space unchanged. We report it as a
concrete instance of a limitation that is usually stated only in the abstract.

### A18. "You claim a switching boundary but never resolve one."

**Where answered:** Results 7.7.
**Answer.** Exactly so, and that is what is reported. Of 19 refined brackets, 13
are monotone and narrow the switching bracket from the 600 veh/h grid to a
median of 150 veh/h *in point estimate*; none of the refined steps is resolved
at five seeds, and 6 sequences are non-monotone. The paper therefore reports the
transition as a point-estimate bracket, states that it is unresolved, and
distinguishes the shortest-path to load-balancing reversal (monotone in all six
cells) from the apparent reliability-aware transitions near it (non-monotone,
consistent with noise).
