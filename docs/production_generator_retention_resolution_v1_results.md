# Production-generator retention resolution — frozen result

## Status

**FROZEN POST-DEVELOPMENT RETENTION RESOLUTION**

Evaluation commit: `849362e061a6d219f2d4b943c0dfed6e746175f0`

## Result

The corrected-eligible universe contains 54 historical response specifications.

The already-frozen primary candidate `d29_kernel`:

- was frozen previously at the production-generator freeze rooted at `bd56c2d`;
- remains `VERIFIED_ELIGIBLE` under the corrected eligibility rule;
- preserves its historical `FAILED_TERMINAL` status under the then-frozen D2.9 gate;
- was retained without ranking or re-optimizing the 54 corrected-eligible points.

Resolution:

`RETAIN_D29_KERNEL_UNDER_MINIMAL_INTERVENTION`

Retained primary candidate:

`d29_kernel`

## Interpretation

This is a retention decision based on minimal intervention and provenance
stability. It is **not** a superiority claim, uniqueness claim, or statistical
selection result.

The result must not be described as showing that `d29_kernel` is the best or
only admissible generator.

## Firewall-evidence naming clarification

The evaluator stores a nested dictionary called `firewall_evidence.checks`.
Its keys have names such as:

`historical_readjudication_D3_worlds_used`

and their values are booleans indicating whether the *required negative
condition* passed.

Therefore a nested value of `True` means:

`historical readjudication D3_worlds_used == False was verified`

—not that D3 worlds were used.

The actual result-level usage flags remain:

- `D3_worlds_used = False`;
- `reserve_30001_30005_used = False`;
- `primary_11001_11030_used = False`;
- `external_TEST_used = False`.

This clarification changes no adjudication or retention logic.

## Mandatory robustness consequence

Because eligibility is non-unique, a separate secondary robustness protocol
representing the endpoint-preserving v2.2 family must be frozen before primary
benchmark execution.

D3 remains paused until this retention freeze is complete and the required
secondary robustness protocol is prospectively specified.
