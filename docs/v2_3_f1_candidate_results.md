# v2.3-F1 Candidate-Family Evaluation

## Status

**Execution commit:** `64f5a6f5c8f429af3b80b62aea2374c29db7d56b`

**Family:** v2.3-F1 headroom-augmented response

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

Every candidate failed the D2.7 scientific Layer-A criterion gates.

For all ten eta values, the failed Layer-A set is:

`C1,C2,C3,C4,C5,C6,C7`.

Thus the admissible set is empty and:

`selected_eta = null`.

## Invariants

Across the complete ladder:

- lower response bounds hold;
- D/I semantic class ceilings are not exceeded;
- headroom remains non-negative;
- the analytic derivative never falls below the historical baseline slope;
- structural-zero pathways remain exactly zero;
- C8-C10 remain exactly unchanged.

## Interpretation

v2.3-F1 solves the reachability weakness observed in v2.2 D4-F1, but the
semantic-headroom-limited architecture does not create sufficient
alternative-context non-separability to meet the scientific Layer-A
references, even at eta=1.

The failure is therefore structural rather than numerical or invariant-related.

## Frozen conclusion

v2.3-F1 is **FAILED / CLOSED**.

Per the v2.3 no-fallback rule, the ladder is not extended, tau is not changed,
and no second response family is introduced inside v2.3 after this result.

Structural-validation seeds `22001–22005`, primary seeds `11001–11030`, and
external TEST remain untouched.
