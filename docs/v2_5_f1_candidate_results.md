# v2.5-F1 Terminal Candidate-Family Evaluation

## Status

**Execution commit:** `869c749c0160fc454f267b4a5b073edfa18e07df`

**Family:** v2.5-F1 ceiling-scaled signed-curvature response

**Frozen ladder:** `eta = 0.1, 0.2, ..., 1.0`

**Outcome:** **FAILED — no eta selected**

No external TEST context, structural-validation seed, or primary seed was
used. Layer-B did not enter selection and the production generator was not
modified.

## Gate behavior

Every candidate passed:

- all D2.8 numerical non-collapse gates;
- all response/invariance gates.

The frozen scientific and reachability gates did not overlap.

- eta=0.1–0.4: Layer-A fails C1–C7; reachability passes.
- eta=0.5: Layer-A fails C1,C3,C6,C7; reachability passes.
- eta=0.6: Layer-A fails C3,C6; reachability passes.
- eta=0.7–0.8: Layer-A fails only C6; C6 reachability fails for
  h_D->C6 and h_E->C6.
- eta=0.9–1.0: all Layer-A criteria pass, but C6 reachability still fails for
  h_D->C6 and h_E->C6.

Thus the admissible set is empty and:

`selected_eta = null`.

## Interpretation

v2.5-F1 successfully removed the v2.4 C6 curvature attenuation strongly enough
for all Layer-A criteria to pass at eta>=0.9. However, the same increase in
ceiling-scaled signed curvature reduced C6 latent-pathway reachability below
its frozen D2.7 references beginning at eta=0.7.

The final development result therefore exposes a genuine structural tradeoff:
within the frozen v2.5 family and eta ladder, the curvature needed to satisfy
all Layer-A criterion gates is incompatible with the reachability required for
C6.

## Terminal conclusion

v2.5-F1 is **FAILED / CLOSED**.

Per the terminal-development rule, no additional response architecture,
criterion-specific modifier, coefficient, or eta extension may be developed
using design seeds `21001–21005`.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched.

If future response redesign is scientifically necessary, it requires a newly
declared development cohort and a new protocol before examining that cohort.
