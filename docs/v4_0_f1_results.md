# v4.0-F1 terminal D2.9-kernel development result

## Status

**FAILED — terminal response-generator development stop rule triggered.**

Evaluation commit: `a54e15ad08121a037740f29a84276376835fbe51`

Development cohort: `29001–29005`

RNG namespace: `2010`

Candidate: `d29_kernel`

Fixed coefficient: `delta = 0.05`

No structural-validation seed, reserve seed, primary seed, or external TEST observation was used.

## Frozen gate outcome

The single pre-specified candidate produced:

- numerical gate: pass;
- invariant gate: pass;
- Layer-A D2.9 gate: fail;
- reachability D2.9 gate: fail;
- all frozen gates: fail.

Failed Layer-A criteria:

`C1, C4, C6, C7`

Failed reachability pathways:

`h_D->C1, h_D->C3, h_D->C4, h_I->C4, h_I->C5, h_T->C3`

## Failure magnitude

The worst Layer-A ratio to its D2.9 threshold was:

- `C6 = 0.669258332`

The worst reachability ratio to its D2.9 threshold was:

- `h_T->C3 = 0.805299227`

The overall joint minimum ratio was therefore:

- `0.669258332`

This is not a boundary/invariance failure. All analytic response constraints passed, including monotonicity, semantic ceilings, structural zeros, endpoint checks, and exact C8–C10 invariance.

## Protocol consequence

The v4.0 protocol was explicitly terminal.

Therefore:

1. do not run structural validation on `22001–22005`, because development failed;
2. do not use reserve seeds `30001–30005`;
3. do not use primary seeds or external TEST;
4. do not tune `delta`;
5. do not change the signed-profile rule and rerun on `29001–29005`;
6. do not open another response-generator family to chase the frozen thresholds.

Response-generator family development is closed at this point. The next methodological action must be to reconsider the benchmark design, scientific estimand, or role of the structural thresholds rather than continue adaptive generator tuning.
