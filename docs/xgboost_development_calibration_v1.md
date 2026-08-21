# XGBoost Development Calibration Protocol v1

## Status

**Frozen before calibration execution.**

Parent state: `6e826e519e3625a85db91f50f4004e26ae1b65b2`.

This protocol closes reproducibility details that were not specified in the
historical v2/v2.1 XGBoost configuration. No XGBoost calibration result has
been observed when these rules are fixed.

## 1. Purpose

Select exactly one `XGBRegressor` hyperparameter configuration on the five
development seeds and freeze it before any primary seed is used.

The calibration cannot use SHAP, MCDM, winner identity, a preferred ITS,
external TEST data, or primary/reserve seeds.

## 2. Existing choices retained unchanged

The following choices are inherited from `config/xgboost.yaml` and are not
reopened:

- estimator: `XGBRegressor`;
- objective: `reg:squarederror`;
- `n_jobs=1`;
- `RandomizedSearchCV`;
- 60 candidate configurations;
- `GroupKFold(5)`;
- optimization metric: RMSE;
- the complete discrete hyperparameter search space already present in
  `config/xgboost.yaml`.

## 3. Development data

Use only seeds:

`21001, 21002, 21003, 21004, 21005`.

For each seed reconstruct the benchmark in memory from the frozen production
source/configuration. Cached legacy development CSVs are not eligible
calibration inputs.

The calibration condition is fixed at:

\[
(N,c,\rho,\lambda)=(250,0.30,0.4,0.5),
\]

with the frozen heterogeneous primary alpha structure and retained production
generator `d29_kernel`.

For each seed, \(s_U\) is computed from all 1000 estimation/calibration
contexts only, excluding external TEST. The model-calibration sample then
uses only the 200 FIT contexts among the first \(N=250\) estimation contexts.

Therefore each seed contributes:

- 200 FIT contexts;
- 1200 FIT alternative-context rows.

Across five seeds the pooled calibration set contains:

- 1000 FIT contexts;
- 6000 alternative-context rows.

WEIGHT rows are not used for hyperparameter selection. External TEST is not
materialized or inspected for calibration.

## 4. Pooling and grouped cross-validation

The five development seeds are pooled with equal design contribution.

Rows are ordered deterministically by:

1. `replication_seed`;
2. `context_number`;
3. `alternative_id`.

Cross-validation uses `GroupKFold(n_splits=5)`. The group identifier is the
globally unique composite `(replication_seed, context_id)`. All six
alternative rows from one context therefore remain in the same fold.

No row from WEIGHT or external TEST enters CV.

## 5. Reproducible randomness

A dedicated seed family is frozen before calibration:

- candidate-sampling random state: `82001`;
- XGBoost estimator random state: `82002`.

The same estimator random state is used for every candidate and fold so that
candidate comparisons are not confounded by different model RNG streams.

Because the search space is fully discrete, 60 configurations are sampled
without replacement from its Cartesian product.

## 6. Selection rule

Scikit-learn scoring is `neg_root_mean_squared_error`.

For candidate \(h\), define:

\[
RMSE_{CV}(h)=\frac{1}{5}\sum_{k=1}^{5}RMSE_k(h).
\]

Select the candidate with minimum mean grouped-CV RMSE.

The SD across folds is reported but does not determine selection.

If candidates are numerically tied within absolute tolerance \(10^{-12}\),
select the lexicographically smallest ascending numeric parameter tuple in
this frozen order:

1. `n_estimators`;
2. `max_depth`;
3. `learning_rate`;
4. `subsample`;
5. `colsample_bytree`;
6. `min_child_weight`;
7. `reg_alpha`;
8. `reg_lambda`.

No second search, search-space extension, performance threshold, SHAP result,
MCDM result, or winner identity may reopen the selection after results are
observed.

`refit=False` is used during the search because this stage selects
hyperparameters; it does not create a final primary model.

## 7. Reporting

The one-shot calibration must save:

- all 60 sampled parameter configurations;
- all five fold RMSE values for every candidate;
- mean and SD grouped-CV RMSE;
- the selected configuration and deterministic tie-break audit;
- descriptive per-seed RMSE for the selected configuration;
- Git commit, package versions, and runtime.

Per-seed diagnostics are descriptive only and cannot change the selected
configuration.

## 8. Firewalls

The calibration must confirm:

- primary seeds `11001–11030`: not used;
- reserve seeds `30001–30005`: not used;
- external TEST: not used;
- WEIGHT: not used for hyperparameter selection;
- SHAP: not used;
- MCDM: not used;
- ITS winner identity: not used;
- TreeSHAP background size: not selected in this stage.

## 9. Execution discipline

Protocol freeze precedes implementation.

Implementation is committed before the first calibration run.

The evaluator is executed once. Results are then checked by an independent
read-only auditor. Only after that audit may the selected values be written
once into `config/xgboost.yaml` and committed as the XGBoost calibration
freeze.

TreeSHAP background calibration begins only after that XGBoost freeze.
