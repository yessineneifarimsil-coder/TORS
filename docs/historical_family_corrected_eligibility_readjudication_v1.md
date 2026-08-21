# Historical response-family corrected-eligibility re-adjudication v1

## Purpose

The post-v4 hard-gate validity audit established that the old simultaneous
D2.9 joint gate is not supported as a binary production-generator eligibility
rule. This protocol therefore re-adjudicates every already-frozen historical
response-family parameter point under the corrected hard constraints only.

The re-adjudication is retrospective and descriptive. It does not rewrite any
historical family failure or candidate-selection record.

## Corrected eligibility

A point is `VERIFIED_ELIGIBLE` only if the frozen record establishes:

1. D2.8 numerical non-degeneracy;
2. analytic/boundary response invariants;
3. structural-zero preservation;
4. C8-C10 invariance.

D2.9 LRV, NSV and SRE ratios are excluded from binary eligibility.

## Family handling

For v2.3 through v4.0, eligibility is recomputed from frozen candidate summaries,
boundary diagnostics and C8-C10 invariance tables.

For v2.2, the artifact schema predates the consolidated invariant fields and
does not include a C8-C10 invariance table. v2.2 must therefore be marked
`INSUFFICIENT_FROZEN_EVIDENCE` unless its frozen source code explicitly proves
that C8-C10 are untouched and all remaining corrected hard constraints are
satisfied. No inference by analogy with later families is allowed.

## No selection

This audit lists every eligible point. It does not choose a production
generator, rank families, maximize structural ratios, or use downstream
benchmark outcomes.

If multiple points are eligible, production-generator selection requires a
separate protocol based on methodological properties independent of SHAP,
MCDM, winner identity or primary-benchmark performance.

## Firewalls

No new simulation, seed, D3 world, reserve cohort, primary cohort or external
TEST is permitted.
