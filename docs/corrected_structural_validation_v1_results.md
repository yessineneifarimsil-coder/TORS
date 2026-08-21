# Corrected one-shot structural validation result

## Outcome

**PASSED — production response generator eligible for freeze.**

Evaluation commit: `a5bb1ba995e6adae8ad7d9e202d8fcf8c8d97f14`

Structural-validation cohort: `22001–22005`

Candidate: `d29_kernel`

Response:

`g(o) = theta*o + 0.05*v*o*(1-o)`

Signed-profile namespace: `2010`

## Corrected hard gates

The one-shot validation passed every frozen hard gate:

- D2.8 numerical non-degeneracy: pass;
- analytic response invariants: pass;
- structural-zero preservation: pass;
- C8–C10 exact invariance: pass.

Therefore:

`VALIDATION_PASSED = True`

and:

`PRODUCTION_GENERATOR_ELIGIBLE_FOR_FREEZE = True`

## D2.9 structural diagnostics

D2.9-normalized LRV/NSV/SRE values were retained as descriptive diagnostics
only and did not determine pass/fail.

Observed minima:

- minimum Layer-A ratio to D2.9: `0.837017960`;
- minimum SRE ratio to D2.9: `0.714925721`.

These values do not reverse the validation decision because the corrected
eligibility protocol prospectively removed D2.9 ratios from binary
production-generator adjudication after the frozen estimand-comparability
audit.

## Firewalls

The validation used only `22001–22005`.

It did not use:

- reserve seeds `30001–30005`;
- primary seeds `11001–11030`;
- external TEST.

No parameter was tuned after observing validation.

## Production freeze consequence

The production response generator is frozen as:

- family: `d29_kernel`;
- formula: `theta*o + 0.05*v*o*(1-o)`;
- delta: `0.05`;
- signed-profile namespace: `2010`;
- criterion noise during structural validation: `sigma_x = 0`;
- no clipping;
- C8–C10 unchanged;
- structural-zero pathways exactly zero.

After this freeze, response-generator development remains closed.

D3 alpha-dispersion calibration may now be unblocked under its previously
specified rule that calibration begins only after the production generator is
frozen.
