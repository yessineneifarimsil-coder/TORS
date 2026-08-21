# TreeSHAP Background Resolution v1

## Status

**FROZEN BEFORE ANY TREESHAP BACKGROUND-SIZE RESULT**

The repository history was audited before this resolution. No frozen empirical
selection metric, background RNG rule, or five-development-seed aggregation
rule was found for choosing among candidate background sizes.

To avoid adding an outcome-driven researcher degree of freedom, the primary
TreeSHAP background size is resolved prospectively rather than selected using
oracle-fidelity, SHAP-vs-oracle, MCDM, winner, or TEST results.

## Frozen choice

Primary background size:

`B_bg = 100`

Historical/provenance sensitivity sizes:

`{25,50,75,100}`

At the binding smallest primary sample, `N=25`, there are 20 FIT contexts and
therefore 120 FIT alternative-context rows. A 100-row background is feasible.

The smaller sizes are descriptive sensitivity values only and cannot replace
100 after TreeSHAP results are observed.

## TreeSHAP contract

- `feature_perturbation="interventional"`
- `model_output="raw"`
- background source: FIT only
- sampling: random without replacement
- selection unit: alternative-context row
- explanation partition: WEIGHT
- global importance: mean absolute SHAP
- local accuracy: absolute and relative tolerance `1e-5`
- external TEST excluded from background construction and SHAP weight estimation

## Deterministic row-priority rule

Namespace `83001` is dedicated to TreeSHAP background row priority.

For replication seed `r`, generate one deterministic random priority ordering
over the complete `N=1000` FIT alternative-context row identities using
`SeedSequence([r,83001])`. For each nested sample size `N`, filter that same
priority ordering to FIT rows available at that `N` and take the first 100.

The priority stream is reused across `rho`, `c`, and `lambda`. Background
membership depends only on row identity and frozen partition membership, not
on feature values, targets, oracle values, SHAP values, MCDM outcomes, winner
identity, or TEST results.

If fewer than 100 eligible FIT rows exist, execution must fail rather than
silently reduce the background size.
