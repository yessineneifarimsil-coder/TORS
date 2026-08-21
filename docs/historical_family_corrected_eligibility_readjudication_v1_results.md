# Historical corrected-eligibility re-adjudication — frozen result

## Status

**FROZEN NONSELECTIVE RETROSPECTIVE RE-ADJUDICATION**

Evaluation commit: `fd94b56b7c66e18f5702eca8daf3c8f0bb32e06d`

This result preserves all historical family labels and recomputes only
corrected production-generator eligibility from frozen artifacts.

## Result

Across 54 historical parameter points:

- `44` are `VERIFIED_ELIGIBLE`;
- `0` are `VERIFIED_INELIGIBLE`;
- `10` are `INSUFFICIENT_FROZEN_EVIDENCE`.

Verified eligible families:

- v2.3: 10 / 10;
- v2.4: 10 / 10;
- v2.5: 10 / 10;
- v3.0: 4 / 4;
- v3.1: 9 / 9;
- v4.0: 1 / 1.

v2.2 contributes 10 points classified as `INSUFFICIENT_FROZEN_EVIDENCE`
because its frozen artifact schema does not establish C8-C10 invariance.

## Corrected eligibility semantics

Eligibility requires all four frozen hard constraints:

1. D2.8 numerical non-degeneracy;
2. analytic/boundary response invariants;
3. structural-zero preservation;
4. C8-C10 invariance.

D2.9 LRV, NSV and SRE are not used as binary eligibility gates.

## Historical status preservation

No historical result is rewritten:

- v2.2 through v3.1 retain historical `FAILED`;
- v4.0 retains historical `FAILED_TERMINAL`.

A point may therefore be historically failed under the then-frozen gate and
retrospectively `VERIFIED_ELIGIBLE` under the corrected eligibility rule.

## Scientific consequence

Corrected eligibility does not uniquely identify v4.0. It defines a broad
eligible set containing 44 frozen historical points.

Therefore production-generator selection must be handled by a separate
prospectively frozen selection protocol. That protocol must not use D2.9
structural ratios, SHAP, MCDM, winner identity, primary-benchmark performance,
or historical trial order as a ranking criterion.

D3 remains paused until production-generator selection is resolved.
