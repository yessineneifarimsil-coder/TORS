# v3.0-F1 Monotone Headroom-Shape Candidate Evaluation

## Status

**Execution commit:** `80b9b52e825ce15e9e60b816acae55d4d70e4964`

**Development cohort:** `23001–23005`

**Reserved cohort:** `24001–24005` (untouched)

**Family:** v3.0-F1 monotone headroom-shape response

**Frozen selectable ladder:** `p = 2, 3, 4, 5`

**Reference:** `p = 1` descriptive only

**Outcome:** **FAILED — no p selected**

No old development seed, reserved seed, structural-validation seed, primary
seed, or external TEST context was used. Layer-B did not enter selection and
the production generator was not modified.

## Gate behavior

Every selectable candidate passed:

- all D2.8 numerical non-collapse gates;
- all frozen response/invariance gates, including:
  - response lower bound;
  - semantic class ceiling;
  - headroom non-negativity;
  - headroom-shape bounds;
  - headroom-shape monotonicity;
  - total derivative floor `g'(o) >= theta`;
  - exact structural zeros;
  - exact C8–C10 invariance.

The scientific gates did not jointly pass:

- `p=2`: reachability passes, but Layer-A fails C1–C7.
- `p=3`: Layer-A fails C1,C2,C4,C5,C6,C7 and `h_E->C6`
  reachability fails.
- `p=4`: Layer-A fails C1,C6 and both `h_D->C6` and `h_E->C6`
  reachability fail.
- `p=5`: Layer-A fails C1,C6 and both `h_D->C6` and `h_E->C6`
  reachability fail.

Thus the admissible set is empty and:

`selected_p = null`.

## Interpretation

v3.0 removed the derivative-loss mechanism that was analytically possible in
the v2.5 signed-curvature family. All observed v3.0 candidates satisfy
`g'(o) >= theta` over the complete admissible domain.

Nevertheless, C6 latent-pathway SRE falls below the frozen D2.7 reachability
references for p>=3, while Layer-A remains below threshold for every selectable
p.

Therefore the v2.5 reachability conflict cannot be attributed solely to the
local derivative falling below the historical theta slope. The normalized
alternative-context geometry used by SRE is also material.

## Development-cohort conclusion

v3.0-F1 is **FAILED / CLOSED** on development seeds `23001–23005`.

Per the frozen v3.0 protocol:

- the p ladder cannot be extended;
- the v3.0-F1 formula cannot be modified using `23001–23005`;
- thresholds cannot be changed;
- no second v3.0 family may be introduced on this cohort.

The reserved block `24001–24005` remains untouched and is not an automatic
fallback.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched.
