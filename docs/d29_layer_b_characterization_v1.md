# D29 Layer-B Characterization Protocol v1

**Status:** frozen before any D29 Layer-B characterization result is computed.

## Purpose

This protocol characterizes the **decision geometry** induced by the already-retained D29
production response kernel. It is descriptive only. It cannot change the corrected-eligible
candidate set, replace D29, create a new generator-selection threshold, or make D29 retrospectively
"best" or "superior".

The D29 production kernel remains

\[
g(o)=\theta o+0.05\,v\,o(1-o)
\]

for active \(C_1\)-\(C_7\) pathways, with exact structural zeros and frozen \(C_8\)-\(C_{10}\).

## Fixed characterization condition

- development seeds: **21001--21005 only**;
- response generator: frozen **D29**;
- context pool: all **1000 estimation/calibration contexts (FIT+WEIGHT)** per seed;
- external TEST: **forbidden**;
- \(\rho=0.4\);
- \(\sigma_x=0\);
- primary heterogeneous oracle \(\alpha\);
- frozen primary interaction graph;
- \(\lambda=0.5\);
- target noise \(Y\): **not generated or used**;
- \(c\): not applicable.

The characterization therefore studies the noise-free oracle decision geometry and does not
evaluate learning, SHAP, weighting methods, or downstream MCDM.

## Frozen tie semantics

All ranking/tie handling uses the already-frozen `decision_semantics_v1` rules:

- absolute tolerance \(10^{-12}\), relative tolerance \(0\);
- complete rankings use anchor-based, non-chaining average-rank tie groups;
- deterministic Top-1 is selected from the true-max tie set, with ascending alternative ID;
- if modal-winner frequencies tie across alternatives, ascending alternative ID resolves the
  modal identity.

## Per-seed outputs

For each development seed, report:

1. number of distinct complete oracle orderings across the 1000 contexts;
2. number of distinct deterministic oracle winners;
3. modal oracle winner identity;
4. modal-winner share;
5. mean normalized oracle regret of the always-select-modal baseline;
6. median normalized oracle regret of that baseline;
7. 95th-percentile normalized oracle regret of that baseline;
8. count of contexts where normalized regret is undefined.

A complete ordering is represented by the tuple of frozen average ranks in
\(A_1,\ldots,A_6\) order. This preserves tie structure rather than silently forcing a strict
lexicographic ordering.

For a context \(s\), normalized regret for the constant modal choice \(a^{modal}\) is

\[
R_s^{modal}
=
\frac{
U^\star_{a^\star_s,s}-U^\star_{a^{modal},s}
}{
\max_a U^\star_{as}-\min_a U^\star_{as}
}.
\]

If the oracle range is \(\le 10^{-12}\), normalized regret is undefined; no epsilon is inserted
into the denominator.

## Cross-seed reporting

All five seed-level results are retained. Descriptive summaries use median, minimum and maximum
across seeds. Winner identity is **never** used as a tuning or retention objective.

## Interpretation firewall

This characterization has **no pass/fail threshold**. Its results may reveal that D29 has weak
or strong decision geometry, but they cannot retrospectively alter the already-frozen
corrected-eligibility set or D29 retention. If the characterization exposes a material
scientific limitation, that limitation must be disclosed. Any decision to introduce a different
response architecture would require a **new protocol version before primary execution**, not an
ad hoc reinterpretation of this diagnostic.

## Execution discipline

The implementation must be committed before execution. The characterization is then executed
once on development seeds 21001--21005. Result overwrite is forbidden. A separate independent,
read-only audit is required before the result artefacts are frozen.

## Firewalls

The characterization must not access:

- external TEST;
- primary seeds 11001--11030;
- reserve seeds 30001--30005;
- structural-validation seeds 22001--22005;
- target \(Y\);
- XGBoost;
- SHAP;
- MCDM weighting methods;
- any preferred ITS winner criterion.
