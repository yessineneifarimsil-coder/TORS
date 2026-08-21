# Post-v4 D2.9 hard-gate validity audit v1

## Status

This audit is opened **after** the D3-B protocol/configuration synchronization
commit but **before any D3 technology world has been generated**.

The D3 synchronization commit is preserved. D3 execution is paused until this
audit is frozen and interpreted.

## Why this audit exists

Seven response-generator families failed the frozen structural gate before the
D2.9 LRV/NSV/SRE ratios were reclassified as continuous diagnostics. The later
estimand-comparability audit established a real mismatch between the D2.9
positive-control profile ensemble and the v3.1/v4.0 candidate ensemble, but it
did not quantify how much that mismatch moved the failing statistics.

Because the corrected rule subsequently made the unchanged v4.0 kernel eligible
for structural validation and production freeze, the quantitative size of the
mismatch must be established before any D3 design world is observed.

This audit does not rewrite any historical pass/fail result and does not use any
protected seed.

## Analysis A — matched profile-ensemble decomposition

Use only the already-consumed v4.0 development cohort `29001–29005`.

For each seed, keep fixed:

- contexts;
- technology-response parameters;
- the frozen production formula
  \(g(o)=\theta o+0.05v\,o(1-o)\);
- rho = 0.4;
- sigma_x = 0;
- every capability and opportunity definition.

Evaluate the candidate in two ways:

1. the already frozen single-profile realization from namespace 2010;
2. the six deterministic D2.9 cyclic rotations.

For the six-rotation version, compute each metric per rotation, take the median
across rotations within seed, then the median across seeds, matching the D2.9
aggregation architecture.

Report for every criterion/pathway:

- frozen single-profile aggregate;
- matched six-rotation aggregate;
- frozen D2.9 reference;
- normalized ratios to D2.9;
- absolute ratio shift;
- fraction of the original shortfall closed.

For C1, C2, C4, C6 and C7 the coefficient support is equivalent. C3 and C5
remain separately flagged because their coefficient supports differ.

The profile-ensemble mismatch fully explains the old v4 hard-gate failure only
if every old Layer-A and reachability hard gate is met under the matched
six-rotation evaluation. If any previously failing support-equivalent
criterion/pathway remains below its D2.9 reference, the mismatch alone does not
fully explain the old failure.

No arbitrary 5% or 30% explanatory cutoff is introduced.

## Analysis B — exact conditional calibration of the old joint gate

Use only the already frozen D2.9 calibration result tables from seeds
`25001–25005`. No new simulation is permitted.

For each seed choose one of its six already observed global rotations. Enumerate
all \(6^5=7776\) rotation combinations.

For every pseudo-candidate, aggregate exactly as a candidate did: median across
the five seeds. Compare LRV50, NSV and SRE against the frozen D2.9 references.

Report:

- pass proportion for each metric;
- joint Layer-A pass proportion;
- joint reachability pass proportion;
- overall joint pass proportion;
- distribution of the minimum normalized ratio.

This is a conditional combinatorial calibration diagnostic, not an independent
frequentist Type-I-error estimate.

## Firewalls

Until this audit is frozen and interpreted:

- the already-committed D3 protocol remains preserved but D3 execution is paused;
- no D3 technology world may be generated;
- reserve `30001–30005` is untouched;
- primary `11001–11030` is untouched;
- external TEST is untouched;
- no response formula, delta, alpha, threshold or seed may be changed;
- SHAP, MCDM, winner identity and downstream method performance may not enter
  the audit.
