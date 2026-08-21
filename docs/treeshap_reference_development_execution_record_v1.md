# TreeSHAP development reference execution record v1

## Status

**AUDITED DEVELOPMENT-ONLY RESULT — FROZEN WITHOUT RERUN**

This record documents the first real TreeSHAP scientific weight computation for
the controlled benchmark development pipeline.

## Chronology and provenance

The scientific TreeSHAP computation protocol was frozen before the first real
SHAP weight vector at commit `626e38d`.

The scientific TreeSHAP computation implementation was then committed and
audited at commit `ba1550f15706099b2e2a57fd8509e72029e877a7` before the first real development
computation.

The development-reference wrapper
`src/treeshap_reference_development_executor_v1.py` had been implemented and its
tests passed, but it had **not yet been committed** when the user invoked it with
`--execute`. This chronology is recorded explicitly and is not rewritten.

The wrapper called the already-committed scientific computation implementation
without altering its frozen model, TreeSHAP, background, normalization,
partition or numerical-accuracy rules.

## Frozen development reference instance

- replication seed: `21001`
- N: `250`
- relative target-noise multiplier c: `0.30`
- predictor-dependence rho: `0.4`
- interaction lambda: `0.5`
- alpha structure: `heterogeneous_fixed`
- production generator: retained `d29_kernel`
- FIT rows used by XGBoost: `1200`
- WEIGHT rows explained by TreeSHAP: `300`
- TreeSHAP background rows: `100`
- external TEST rows evaluated: `0`
- MCDM executed: `false`

The complete 1200-context / 7200-row master was deterministically reconstructed
because the frozen pipeline requires it for partition integrity and for the
relative-noise construction. External TEST rows were not used for signal-SD
estimation, model fitting, background construction, SHAP-weight estimation or
decision evaluation.

## Numerical audit

- SHAP weight vector defined: `true`
- total SHAP importance: `0.070061310111830408`
- local-accuracy maximum absolute error:
  `6.4500187207938708e-07`
- local-accuracy maximum scaled error:
  `0.05023271220640356`
- background identity SHA-256:
  `3184c675397c8caf547a8da7f68d04a589b949ce39a1953bbf55d4461646eda1`

The independent read-only audit verified that the ten importances are finite and
nonnegative, their sum equals the recorded total importance, the normalized
weights sum to one, each weight equals its importance divided by total
importance, and the frozen local-accuracy invariant is satisfied on every
WEIGHT row.

## Preservation hashes

- executor SHA-256:
  `80a5f8cc35c2e74e5685ed2fee9b0d6c99c8c731c48c7a34aa8d0e425145253f`
- executor test SHA-256:
  `83103d61a1eae881248d7a7fb36215b43b7190a3a057dd309639df347f3e6207`
- result JSON SHA-256:
  `dee9fac2357e195aaa5dbaaec9066fffc2f1e9c6151dfb35fede873e3fbe4256`

These hashes identify the exact wrapper, test and result that existed at the
time of the independent post-execution audit.

## Scientific role and firewall

This result is **development reference only**. It is not primary evidence and
must not be used to tune or redefine:

- SHAP computation or normalization;
- XGBoost hyperparameters or learner RNG;
- TreeSHAP background size or membership rule;
- CRITIC, Entropy, Ridge+, permutation importance or Equal weighting;
- MOORA or TOPSIS semantics;
- decision-fidelity metrics;
- Pilot B thresholds or hard-stop rules;
- preferred weighting-method or ITS winner requirements.

SHAP weights remain predictive attribution-derived surrogate weights. They are
not causal effects, stakeholder preferences, normative weights or social-welfare
weights.

The existing JSON result is frozen **without rerun**.
