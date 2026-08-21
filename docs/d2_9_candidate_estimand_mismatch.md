# D2.9–candidate estimand comparability audit

## Finding

A post-v4.0 methodological audit identified a genuine comparability limitation
between the D2.9 positive-control reference statistics and the candidate-family
statistics used for hard adjudication.

This finding does **not** alter any frozen historical result. It changes only the
scientific interpretation of D2.9 as a direct hard feasibility threshold.

## What is comparable

For criteria with all six alternatives active (C1, C2, C4, C6, C7), the D2.9
contrast support

`[-1, -0.6, -0.2, 0.2, 0.6, 1]`

and the v4.0 `signed_grid(6)` support are numerically equivalent up to ordinary
floating-point representation.

The earlier exact-array `False` result is therefore not a substantive
difference.

## First substantive mismatch: profile ensemble and aggregation

D2.9 evaluates six deterministic cyclic rotations per seed and criterion.
Its Layer-A and reachability references are formed by:

`median over rotations within seed -> median over seeds`.

v4.0 evaluates one random signed-profile permutation per seed and criterion,
then uses:

`median over seeds`.

The two procedures therefore estimate different profile-ensemble functionals.

For six active alternatives, D2.9 samples six cyclic permutations, whereas a
full signed-profile permutation space contains 720 permutations.

## Second substantive mismatch: C3 and C5 coefficient support

C3 and C5 each have only five active alternatives.

v4.0 therefore uses:

`[-1, -0.5, 0, 0.5, 1]`.

D2.9 assigns its six-position contrast before structural-zero alternatives are
removed from the criterion-specific active set. Across the six rotations, the
active alternatives therefore inherit values from:

`[-1, -0.6, -0.2, 0.2, 0.6, 1]`.

Thus C3 and C5 differ not only in profile ensemble but also in coefficient
support.

## Consequence

D2.9 remains a valid and useful admissible positive-control calibration.

However, its values should not be treated as directly comparable binary
production-generator feasibility thresholds for the single-profile candidate
ensemble used in v3.1/v4.0.

Historical v2.2–v4.0 outcomes remain frozen exactly as observed. They must not be
retroactively relabeled as passes. The correct statement is that they failed
their then-frozen gates, while a later methodological audit showed that those
scientific gates compared non-identical profile-ensemble estimands.

## Forward design rule

Hard eligibility constraints should be restricted to quantities whose
interpretation is invariant to the positive-control profile ensemble:

- analytic response admissibility;
- structural-zero preservation;
- C8–C10 invariance;
- D2.8 numerical non-degeneracy.

LRV, NSV and SRE should be retained as continuous structural diagnostics.
Positive-control-normalized ratios may still be reported descriptively, but
`ratio >= 1` should not be used as a binary production-generator eligibility
criterion unless the calibration and candidate profile ensembles are first made
estimand-compatible under a new prospectively frozen design.
