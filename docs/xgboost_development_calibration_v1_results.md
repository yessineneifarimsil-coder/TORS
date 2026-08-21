# XGBoost Development Calibration v1 — Frozen Result

## Status

**Frozen after independent audit.**

The one-shot calibration was executed from commit
`247bf8939fe52c8dd32ba3ae41e12e17f3108b92` on the dedicated development
seeds `21001–21005`. The result was independently audited before the selected
parameters were written into `config/xgboost.yaml`.

The calibration executor must not be rerun.

## Calibration sample

The frozen reference condition was:

(N, c, rho, lambda) = (250, 0.30, 0.4, 0.5).

The retained production response generator was `d29_kernel`.

Each of the five development seeds contributed 200 FIT contexts. The pooled
calibration sample therefore contained:

- 1,000 independent FIT context groups;
- 6,000 alternative-context rows.

Five-fold `GroupKFold` preserved the context as the independent grouping unit,
so all six alternative rows belonging to one context remained in the same
fold.

## Candidate search

The already-frozen discrete XGBoost search space was sampled using:

- `RandomizedSearchCV`;
- 60 unique candidates;
- candidate-sampling random state `82001`;
- estimator random state `82002`;
- `GroupKFold(5)`;
- optimization statistic: mean grouped-CV RMSE.

The exact 60-candidate sequence had SHA-256:

`b1c76b23873d6001a60cc78060d5fc4c10686531770558bbd99e125e86e201a9`

This hash matched the pre-execution audit.

## Selected model

Candidate 45 was the unique minimum under the frozen selection rule.

Mean grouped-CV RMSE:

`0.017757058913365983`

Frozen parameters:

| Parameter | Value |
|---|---:|
| `n_estimators` | 600 |
| `max_depth` | 2 |
| `learning_rate` | 0.05 |
| `subsample` | 0.8 |
| `colsample_bytree` | 0.8 |
| `min_child_weight` | 5 |
| `reg_alpha` | 0.0 |
| `reg_lambda` | 1.0 |

The five selected-candidate OOF fold RMSE values were descriptive development
diagnostics only. Fold-to-fold SD is not treated as an inferential standard
error.

## Firewalls

The independent audit confirmed:

- no primary seed `11001–11030` was used;
- no reserve seed `30001–30005` was used;
- WEIGHT rows did not enter hyperparameter selection;
- external TEST did not enter signal-SD estimation, fitting or grouped CV;
- no external-TEST performance metric was inspected;
- SHAP, MCDM and winner identity did not influence model selection;
- no legacy cached development CSV was used;
- TreeSHAP background size was not selected in this stage.

The development RMSE is a calibration statistic, not a primary RQ1 result.

## Next dependency

XGBoost calibration is now closed. The next development dependency is the
pre-specified TreeSHAP background reassessment and freeze on development seeds
only. The candidate set must include the now-feasible 100-row background
before any primary execution.
