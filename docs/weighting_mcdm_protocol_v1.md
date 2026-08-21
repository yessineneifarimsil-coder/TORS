# Weighting and MCDM protocol v1

## Status

**FROZEN BEFORE WEIGHTING/MCDM IMPLEMENTATION AND BEFORE PILOT B**

This protocol closes implementation-level degrees of freedom that remained after
the audited TreeSHAP development reference. The choices below are fixed for
reproducibility and may not be altered in response to the observed SHAP weight
vector, method performance, or the identity of any ITS winner.

## Attribution and weighting rules

Oracle attribution uses the already-specified closed-form interventional oracle
Shapley definition. Global importance is mean absolute attribution on WEIGHT
using FIT background moments. If total oracle attribution importance is at most
`1e-12`, the oracle attribution weight vector is undefined; Equal weights are
not substituted and Oracle-weight MCDM is not computed for that instance.

Permutation Importance uses the fitted XGBoost model, WEIGHT MSE, and 20 unique
context-block derangements. A dedicated seed family `84001` is used. For each
replication seed and N, derive the derangement RNG from
`SeedSequence([replication_seed, 84001, N])`. Sort WEIGHT contexts by
`context_number` and index them `0..m-1`. Repeatedly draw
`perm = rng.permutation(m)`; accept only candidates with no fixed position and
whose tuple has not previously been accepted. Stop after 20 unique candidates;
if this is not achieved within 100000 draws, raise `RuntimeError` with no
fallback. For destination position `d`, copy the permuted criterion's complete
six-alternative block from source position `perm[d]`, preserve ascending
`alternative_id` within the block, and leave every other feature unchanged.
The same 20 accepted derangements are reused for all ten criteria and across
rho, c, and lambda. Negative mean importances are truncated to zero; if all are
non-positive, Equal weights are used and the event is recorded.

Ridge+ standardizes X and y with population (`ddof=0`) statistics. CV
standardization is fitted within each training fold only; the final fit uses
full-FIT statistics. There is no intercept in standardized space. Features with
standard deviation at most `1e-12` are represented by zero standardized columns
and their coefficients are fixed at zero. A degenerate y produces all-zero
coefficients and therefore the already-specified Equal fallback. Production
uses `scipy.optimize.nnls` on the L2-augmented design. Five-fold GroupKFold does
not shuffle; RMSE is scored after returning predictions to the original Y scale.
If mean CV RMSE values tie within `1e-12`, choose the smallest tau.

CRITIC and Entropy use the primary WEIGHT-only min-max matrix. CRITIC uses
population SD (`ddof=0`). Effectively constant criteria receive zero information
and are excluded from correlation-conflict sums for nonconstant criteria.
Entropy uses n equal to the number of alternative-context rows in WEIGHT and
retains `0 log 0 = 0`. Existing Equal fallbacks remain unchanged.

Equal weights remain 0.1 per criterion.

## Diagnostic references

Random weights use 200 `Dirichlet(1,...,1)` draws derived from
`SeedSequence([replication_seed, 81001])`; the same 200 vectors are reused across
N, rho, c, and lambda within a replication seed.

The modal-winner baseline estimates the oracle modal winner on WEIGHT. Oracle
utility ties and modal-count ties are resolved by ascending `alternative_id`
using an absolute score-tie tolerance of `1e-12`.

## MCDM

MOORA retains the frozen benefit-oriented ratio-system definition:

`r_asj = g_asj / (sqrt(sum_a g_asj^2) + 1e-12)`

and `S_as = sum_j w_j r_asj`, ranked descending.

TOPSIS uses the same normalized benefit-oriented matrix. Let
`v_asj = w_j r_asj`. The positive ideal is the columnwise maximum and the
negative ideal the columnwise minimum. Euclidean distances are used and
closeness is `D_minus/(D_plus + D_minus)`. If `D_plus + D_minus <= 1e-12`,
closeness is set to 0.5. Alternatives are ranked by descending closeness.

For MOORA, TOPSIS, Direct-XGBoost scores, and other method-score rankings,
the absolute tie tolerance is `1e-12`. Sort raw scores descending and then
`alternative_id` ascending. Use the highest unassigned score as each tie-group
anchor; include every remaining score within `1e-12` of that anchor, assign
the group its average rank, and repeat. Do not chain adjacent near-ties. For
Top-1, the tie set is every alternative within `1e-12` of the maximum score;
select ascending `alternative_id` within that set.

## Stage-wise decision-fidelity diagnostics

The stage-wise analysis is descriptive and diagnostic, not an additive error
decomposition. The frozen representations are:

1. `OracleUtility`
2. `OracleMainEffectReference`
3. `OracleGlobalAttributionNonlinearQ`
4. `SHAPGlobalAttributionNonlinearQ`
5. `OracleGlobalAttributionLinearG`
6. `SHAPGlobalAttributionLinearG`
7. `OracleWeightMOORA`
8. `SHAPWeightMOORA`
9. `DirectXGBoost`

`DirectXGBoost` is a parallel predictive-decision reference rather than a
sequential transformation stage.

## Pilot B diagnostic prerequisites

Pilot B requires `DirectXGBoost`, 200 `RandomWeights` Dirichlet draws, and
`MajorityWinner`. Numerical hard-stop thresholds are not fixed here; they
must be frozen prospectively before any Pilot B result is inspected.

## Scientific firewall

External TEST is never used to fit XGBoost, estimate SHAP or oracle weights,
compute PI, fit/tune Ridge+, or estimate CRITIC/Entropy weights. Primary/reserve
results, preferred ITS identity, and observed SHAP weights cannot change this
protocol.
