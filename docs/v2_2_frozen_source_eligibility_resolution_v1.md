# v2.2 frozen-source eligibility evidence resolution v1

## Why this protocol is necessary

The frozen historical corrected-eligibility re-adjudication classified all ten
v2.2 points as `INSUFFICIENT_FROZEN_EVIDENCE` because v2.2 predates the
dedicated `c8_c10_invariance.csv` artifact used by later families.

That same re-adjudication protocol explicitly allowed v2.2 to become verified
eligible if its **frozen source-code contract** establishes C8-C10 invariance
and the remaining corrected hard constraints are already established.

A later read-only formula/semantics inventory exposed evidence that the v2.2
evaluator may indeed contain such a contract. This protocol freezes how that
evidence will be adjudicated before a formal result is produced.

## Historical-source requirement

The source must be read from the contemporaneous v2.2 freeze commit:

`37c8f31 Freeze failed v2.2 D4-F1 candidate evaluation`

The current working-tree copy is not sufficient by itself.

## Corrected eligibility evidence

For each historical v2.2 kappa point, corrected eligibility requires:

1. frozen D2.8 numerical non-degeneracy pass;
2. frozen boundary constraints pass;
3. frozen structural-zero preservation pass;
4. C8-C10 invariance established by explicit contemporaneous source contract.

D2.9 LRV/NSV/SRE are excluded from binary eligibility.

## Source-contract standard

C8-C10 invariance is established only if the historical source makes clear that:

- the candidate-response rewrite is confined to C1-C7;
- C8-C10 are preserved from the baseline and are not overwritten;
- structural-zero pathways remain exact zero;
- admissibility is not created by clipping C8-C10 or by downstream repair.

## Historical preservation

The previous `44 VERIFIED_ELIGIBLE / 10 INSUFFICIENT_FROZEN_EVIDENCE` freeze is
not rewritten. If v2.2 is verified, this result is recorded as a supplemental
evidence-resolution audit for the later production-generator selection universe.

No production generator is selected here.

## Firewalls

No new simulation, new seed, D3 world, reserve cohort, primary cohort, external
TEST, SHAP, MCDM, winner identity, D2.9 structural ranking, or response-parameter
change is permitted.
