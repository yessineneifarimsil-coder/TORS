# D2.9 Admissible Positive-Control Recalibration — Frozen Results

## Status

**Execution commit:** `3463d5d294798e8d2770d6c95ee63ecf01230dca`

**Calibration cohort:** `25001–25005`

**Reserved cohort:** `26001–26005` (untouched)

**Outcome:** **CALIBRATION VALID AND REPRODUCIBLE**

The corrected positive control was

\[
g^{PC+}(o)=\theta o+0.05\,c\,o(1-o).
\]

The actual maximum absolute response departure was

\[
|\Delta g|_{\max}=0.0125.
\]

## Admissibility

The frozen calibration produced:

- 1260 total diagnostic rows;
- 1200 active-pathway rows;
- zero lower-bound violations;
- zero semantic-ceiling violations;
- zero monotonicity violations;
- zero structural-zero violations;
- minimum analytic derivative floor = `0.0`;
- maximum absolute response departure = `0.0125`.

## Frozen Layer-A references

| Criterion | T_sci_LRV | T_sci_NSV_vector |
|---|---:|---:|
| C1 | 0.0823367060180439 | 0.04150944500477258 |
| C2 | 0.05135703082499147 | 0.030180789560001246 |
| C3 | 0.06320131683925327 | 0.032871176397166704 |
| C4 | 0.0584394716346404 | 0.033274732045588784 |
| C5 | 0.06114512257795974 | 0.03893229936662514 |
| C6 | 0.10669498984969662 | 0.06203584559273667 |
| C7 | 0.06752862595487336 | 0.0421069255807601 |

## Frozen reachability references

| Pathway | T_sci_SRE |
|---|---:|
| h_D->C1 | 0.6252491501173607 |
| h_D->C2 | 0.3049148696475096 |
| h_D->C3 | 0.4220320343087468 |
| h_D->C4 | 0.32269510335210616 |
| h_D->C6 | 0.4123214319717975 |
| h_D->C7 | 0.27257109898658916 |
| h_E->C6 | 0.27555688651992993 |
| h_I->C2 | 0.20048975060267737 |
| h_I->C4 | 0.3327413283163435 |
| h_I->C5 | 0.5701057397882139 |
| h_T->C3 | 0.29261826954559067 |
| h_T->C7 | 0.41859298239010767 |

## Aggregation semantics

D2.9 preserves the frozen D2.7 aggregation rule:

1. median across six rotations within each calibration seed;
2. median across the five seed-level medians.

## Layer-B

Layer-B remains descriptive only:

- `activated = false`;
- `T_R_sci = null`;
- Layer-B was not used to define a scientific selection threshold.

## Firewalls

The calibration did not use external TEST, structural-validation seeds
`22001–22005`, primary seeds `11001–11030`, old D2.7 design seeds
`21001–21005`, v3.0 development seeds `23001–23005`, or reserved seeds
`26001–26005`.

D2.8 numerical-null thresholds were not modified.

## Reproducibility

The final run was reproduced from the same execution commit and all nine
output artifacts were byte-for-byte identical.

Historical D2.7 thresholds remain preserved for provenance but are superseded
for future scientific-gate adjudication.
