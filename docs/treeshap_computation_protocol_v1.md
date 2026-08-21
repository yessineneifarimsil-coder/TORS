# TreeSHAP Scientific Computation Protocol v1

## Status

**FROZEN BEFORE THE FIRST SCIENTIFIC SHAP WEIGHT VECTOR**

Parent commit: `8626235608fcb8d052223d6793387458280a63f4`.

The TreeSHAP background size and constructor are already frozen. This protocol
does not reopen `B_bg=100`. It closes the remaining scientific computation
semantics before any real benchmark `w^SHAP` is observed.

## XGBoost fit

For every seed-by-factorial benchmark instance, fit one `XGBRegressor` on FIT
rows only, using `g_C1,...,g_C10` to predict noisy target `Y`.

Use the already-frozen hyperparameters:

- n_estimators = 600
- max_depth = 2
- learning_rate = 0.05
- subsample = 0.8
- colsample_bytree = 0.8
- min_child_weight = 5
- reg_alpha = 0.0
- reg_lambda = 1.0

Use `objective="reg:squarederror"`, `n_jobs=1`, `verbosity=0`, no early
stopping, and no eval set.

FIT rows are sorted by `(context_number, alternative_id)` before fitting.

### Learner RNG

Use `random_state=82002` for every scientific XGBoost fit.

This deliberately reuses the already-frozen estimator RNG from development
calibration. It is held fixed across replication seeds and all factorial cells
so learner-internal stochasticity is controlled rather than added to the
benchmark-instance stochastic structure.

## TreeSHAP computation

Use the committed background constructor with exactly 100 FIT rows.

The validated API is:

```python
explainer = shap.TreeExplainer(
    model=model,
    data=background,
    feature_perturbation="interventional",
    model_output="raw",
)
explanation = explainer(X_weight)
phi = explanation.values
base = explanation.base_values
```

WEIGHT rows are sorted by `(context_number, alternative_id)` before
explanation.

External TEST rows do not enter model fitting, background construction, or
global SHAP-weight estimation.

## Local accuracy

For each WEIGHT row, require:

`base_value + sum_j(phi_j) ~= model.predict(x)`

with absolute and relative tolerances `1e-5`.

The elementwise rule is:

`abs(error) <= 1e-5 + 1e-5*abs(prediction)`.

This is a numerical correctness invariant, not a scientific performance gate.
If it fails, the instance emits no SHAP weights and raises a numerical error.

Record maximum absolute error and maximum scaled error.

## Global attribution compression

For criterion j:

`I_j = mean over WEIGHT rows of abs(phi_ij)`.

Then, if:

`sum_j I_j > 1e-12`,

define:

`w_j = I_j / sum_k I_k`.

All six alternatives occur for every WEIGHT context, so row averaging gives
equal total contribution to every context.

### Degenerate total importance

If total importance is less than or equal to `1e-12`, do **not** substitute
equal weights.

Instead:

- mark `undefined_shap_weight_vector=true`;
- do not compute SHAP-MCDM outputs for that instance;
- continue other benchmark methods;
- report the degeneracy event.

This prevents a failed/constant attribution estimate from being silently
relabelled as the Equal-weight method.

## Persisted outputs

Persist at minimum:

- global importance vector;
- global SHAP weight vector when defined;
- local-accuracy diagnostics;
- background identity hash;
- FIT, WEIGHT and background row counts;
- model random state;
- package versions and Git commit.

Full row-level SHAP matrices need not be retained for every primary instance;
they may be retained for reference diagnostics.

## Firewalls

Neither oracle attribution fidelity, MCDM performance, winner identity,
preferred ITS identity nor external TEST results may modify the SHAP
computation or normalization rule.
