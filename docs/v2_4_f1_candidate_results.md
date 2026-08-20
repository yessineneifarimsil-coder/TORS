# v2.4-F1 Candidate-Family Evaluation

## Status

**Execution commit:** `56ac899ccddfb9d5735cc6209a65af1e946ff0f3`

**Family:** v2.4-F1 compensated signed-curvature response

**Frozen ladder:** `eta = 0.1, 0.2, ..., 1.0`

**Outcome:** **FAILED — no eta selected**

No external TEST context, structural-validation seed, or primary seed was
used. Layer-B did not enter selection and the production generator was not
modified.

## Gate behavior

Every candidate passed:

- all D2.8 numerical non-collapse gates;
- all frozen latent-pathway reachability gates;
- all response/invariance gates.

Every candidate failed the complete D2.7 scientific Layer-A criterion gate.

The Layer-A failure set progressively shrank with eta:

- eta=0.1–0.5: C1–C7 fail;
- eta=0.6: C1,C2,C3,C4,C6,C7 fail;
- eta=0.7: C1,C3,C4,C6,C7 fail;
- eta=0.8: C1,C3,C6,C7 fail;
- eta=0.9: C1,C6,C7 fail;
- eta=1.0: only C1 and C6 fail.

Thus the admissible set is empty and:

`selected_eta = null`.

## Interpretation

v2.4-F1 preserved the reachability and invariant strengths of v2.3-F1 while
substantially improving scientific Layer-A non-separability. However, the
frozen ladder still did not satisfy all criterion-level references: C1 and C6
remained below threshold at eta=1.0.

The family is therefore structurally improved but not admissible under the
frozen v2.4 selection rule.

## Frozen conclusion

v2.4-F1 is **FAILED / CLOSED**.

Per the v2.4 no-fallback rule, eta is not extended above 1.0 and no second
response family is introduced inside v2.4 after observing this result.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched.
