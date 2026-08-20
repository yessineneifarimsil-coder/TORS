# v2.2 D4-F1 Candidate-Family Evaluation

## Status

**Execution commit:** `575358303293ae102a3d64721aab71ba4df67b9b`

**Family:** D4-F1 alternative-specific monotone curvature tilt

**Frozen ladder:** `0.1, 0.2, ..., 1.0`

**Outcome:** **FAILED — no kappa selected**

No external TEST context, structural-validation seed, or primary seed was used.
Layer-B diagnostics were not used for selection, and the production response
generator was not modified.

## Gate behavior

All ten candidates passed the D2.8 numerical non-collapse gates.

Scientific Layer-A behavior improved monotonically in the sense relevant to the
frozen selection summary:

- `kappa=0.1–0.4`: C1–C7 fail;
- `kappa=0.5`: C1, C3, C4, C6, C7 fail;
- `kappa=0.6`: C1, C3, C6, C7 fail;
- `kappa=0.7–0.8`: only C6 fails;
- `kappa=0.9–1.0`: all C1–C7 scientific Layer-A gates pass.

However, no candidate passed the frozen latent-pathway reachability gates.

At `kappa=0.1`, only `h_D->C2` and `h_I->C2` fail reachability.
As curvature increases, more pathways fall below their D2.7 SRE references.
At `kappa=0.9` and `1.0`, all 12 declared pathways fail.

Thus the family successfully breaks v2.1 multiplicative collapse but does not
preserve sufficient relative latent-factor reachability at the curvature levels
required to satisfy the scientific Layer-A references.

## Frozen conclusion

The pre-specified selection set is empty:

`selected_kappa = null`.

D4-F1 therefore fails under the frozen v2.2 rules.

The family must not be extended, retuned, or supplemented with a new candidate
architecture inside v2.2 after observing this result. Structural-validation
seeds `22001–22005`, primary seeds `11001–11030`, and external TEST remain
untouched for redesign selection.

Any new response architecture belongs to a new protocol version.
