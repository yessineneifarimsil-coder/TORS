# v2.2 D2.8 Numerical-Null Calibration Results

## Status

**Execution commit:** `a1f2e54ff8965654cbf2e0773a1e249cd22170f7`

**Branch:** `protocol-v2.2-design`

D2.8 was executed only after its numerical-null design and implementation had been preregistered and committed.

No candidate response, external TEST context, or primary seed was used.

## Frozen numerical thresholds

\[
T^{num}_{NS} = 10^{-12}
\]

\[
T^{num}_{LRV} = 10^{-10}
\]

\[
T^{num}_{NSV,vector} = 3.2506084454037334\times 10^{-8}.
\]

The corresponding pooled null `Q0.999` values are:

- `Q999_NS_null = 0.0`;
- `Q999_LRV_null_max = 9.87998515262175e-16`;
- `Q999_NSV_vector_null = 3.250608445403733e-10`.

The M-A1 energy floor is `1e-24`.

## Historical v2.1 characterization

The preregistered descriptive check evaluated design seeds `21001–21005`, `rho=0.4`, `sigma_x=0`, FIT+WEIGHT only, and C1–C7 active alternatives only.

All `35 = 5 seeds × 7 criteria` historical checks fall below all three frozen numerical thresholds.

Observed maxima:

- `max historical NS = 0.0`;
- `max historical LRV = 7.222425309945365e-16`;
- `max historical vector NSV = 1.803557624200258e-09`.

These thresholds are numerical collapse discriminators only. They do not replace the D2.7 scientific LRV/NSV/SRE references.

D2.8 is closed before any D4-F1 candidate-family execution.
