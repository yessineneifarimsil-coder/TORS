# Corrected production-generator eligibility protocol

## Status

**Prospectively opened before any structural-validation seed was evaluated under the corrected rule.**

Parent commit: `84867e1dbe24cdad8023c39596afe11d554156a3`

This protocol follows the frozen post-v4.0 estimand-comparability audit.

## Historical record is preserved

The historical v4.0 result remains:

- `FAILED_TERMINAL` under its original frozen D2.9 hard-gate protocol;
- no historical file is rewritten;
- no historical pass/fail label is changed.

The corrected rule is therefore **not** a retroactive relabeling of the old
experiment.

## Why the eligibility rule changes

The frozen comparability audit established that D2.9 and v3.1/v4.0 did not
estimate the same signed-profile ensemble functional:

- D2.9: six deterministic cyclic rotations per seed, followed by a within-seed
  median and then a between-seed median;
- v4.0: one random criterion-specific signed-profile realization per seed,
  followed by a between-seed median.

In addition, C3 and C5 used different coefficient supports.

Therefore D2.9 remains a valid positive-control calibration, but its LRV, NSV
and SRE reference values are not directly comparable binary production
eligibility thresholds for the v4.0 ensemble.

## Corrected hard eligibility constraints

A production-generator candidate is eligible for structural validation only if
all of the following hold:

1. frozen D2.8 numerical non-degeneracy passes;
2. analytic lower-bound constraints pass;
3. semantic class ceilings pass;
4. monotonicity passes;
5. structural-zero pathways remain exactly zero;
6. response endpoints satisfy the frozen analytic definition;
7. C8–C10 remain exactly unchanged.

No D2.9 LRV, NSV or SRE ratio is a binary eligibility gate.

## Role of D2.9 after correction

D2.9 remains in the benchmark as a calibrated admissible positive control.

The following remain reportable **continuous diagnostics**:

- LRV;
- NSV;
- SRE;
- LRV / D2.9 reference;
- NSV / D2.9 reference;
- SRE / D2.9 reference.

A ratio below 1 is not, by itself, a production-generator rejection criterion.

## Retrospective methodological re-adjudication of frozen v4.0 development

No response family is re-run and no parameter is changed.

The already frozen v4.0 development artifacts are re-read only to answer the
new eligibility question.

Under the corrected hard constraints, the frozen v4.0 candidate:

- passes D2.8 numerical non-degeneracy;
- passes all response invariants;
- is therefore **eligible for one-shot structural validation**.

This statement does not alter its historical `FAILED_TERMINAL` label under the
old protocol.

## One-shot structural validation

Only the already protected structural-validation cohort `22001–22005` may be
used.

The v4.0 generator must be evaluated **exactly once** with:

- the same response formula;
- the same fixed `delta = 0.05`;
- the same signed-profile construction;
- namespace `2010`;
- rho `0.4`;
- sigma_x `0`;
- lambda `0.5`;
- FIT+WEIGHT contexts only;
- external TEST excluded.

No parameter may be selected, tuned, or changed after observing validation.

### Validation hard gates

On `22001–22005`, the generator must again pass:

- D2.8 numerical non-degeneracy;
- all analytic response invariants;
- structural-zero preservation;
- exact C8–C10 invariance.

LRV, NSV, SRE and their D2.9-normalized ratios are reported but do not determine
validation pass/fail.

### Validation outcome

If all corrected hard gates pass:

- freeze v4.0 as the production response generator;
- then unblock D3 alpha-dispersion calibration.

If any corrected hard gate fails:

- structural validation fails;
- do not switch to a fallback generator;
- do not use reserve seeds as backup validation;
- revisit the benchmark design rather than opening another tuned family.

## Protected data after this protocol

Until one-shot structural validation succeeds and the production generator is
frozen:

- reserve seeds `30001–30005` remain untouched;
- primary seeds `11001–11030` remain blocked;
- external TEST remains blocked;
- D3 remains blocked.
