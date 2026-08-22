from __future__ import annotations

"""Frozen non-negative Ridge (Ridge+) weighting implementation.

Ridge+ is fitted on FIT only and uses the noisy target Y. Within each of five
GroupKFold splits, X and Y standardization statistics are estimated from that
training fold only (population SD, ddof=0). The standardized NNLS problem has
no intercept. The final model is refitted with full-FIT statistics.

WEIGHT and external TEST rows, oracle utility, SHAP values, MCDM scores, and
winner identities are not used.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.model_selection import GroupKFold


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
EPSILON = 1.0e-12
EQUAL_WEIGHT = 0.1
CV_FOLDS = 5
TIE_ABSOLUTE_TOLERANCE = 1.0e-12
CANDIDATE_TAU = (0.0001, 0.001, 0.01, 0.1, 1.0, 10.0, 100.0)

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_FIT_ROWS = {25: 120, 50: 240, 100: 480, 250: 1200, 1000: 4800}
EXPECTED_FIT_CONTEXTS = {25: 20, 50: 40, 100: 80, 250: 200, 1000: 800}
SORT_COLUMNS = ("context_number", "alternative_id")


@dataclass(frozen=True)
class StandardizedNNLSFit:
    coefficients: np.ndarray
    x_mean: np.ndarray
    x_sd: np.ndarray
    active_feature_mask: np.ndarray
    y_mean: float
    y_sd: float
    y_constant: bool
    residual_norm: float
    tau: float


@dataclass(frozen=True)
class RidgeCVResult:
    selected_tau: float
    mean_rmse_by_tau: dict[float, float]
    fold_rmse_by_tau: dict[float, tuple[float, ...]]
    folds: int
    group_count: int


@dataclass(frozen=True)
class RidgePlusWeightResult:
    replication_seed: int
    n_contexts: int
    weights_by_feature: dict[str, float]
    coefficients_by_feature: dict[str, float]
    selected_tau: float
    mean_cv_rmse_by_tau: dict[float, float]
    fold_cv_rmse_by_tau: dict[float, tuple[float, ...]]
    zero_variance_features: tuple[str, ...]
    diagnostics: dict[str, Any]


def prepare_ridge_fit_rows(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> pd.DataFrame:
    """Return exact nested FIT rows in deterministic order."""
    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")

    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        "Y",
        *FEATURES,
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Ridge+ input is missing columns: {missing}.")
    if rows.empty:
        raise ValueError("Ridge+ input must not be empty.")

    nested = rows.loc[rows["context_number"].le(n)].copy()
    if nested.empty:
        raise ValueError("No nested estimation rows found for requested N.")
    unexpected_partitions = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected_partitions:
        raise ValueError(
            "Unexpected partition labels inside nested estimation scope: "
            f"{unexpected_partitions}."
        )

    # Frozen FIT-only firewall: WEIGHT scientific values are excluded before
    # seed, identity, feature, and target validation.
    selected = nested.loc[nested["partition"].eq("fit")].copy()
    if selected.empty:
        raise ValueError("No FIT rows found for requested N.")

    if selected["replication_seed"].isna().any():
        raise ValueError("FIT replication_seed contains missing values.")
    observed_seeds = set(selected["replication_seed"].astype(int).tolist())
    if observed_seeds != {int(replication_seed)}:
        raise ValueError(
            f"FIT Ridge+ rows must contain exactly replication_seed={replication_seed}; "
            f"found {sorted(observed_seeds)}."
        )
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate FIT context-alternative rows detected.")

    x = selected.loc[:, FEATURES].to_numpy(dtype=float)
    y = selected["Y"].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("FIT Ridge+ feature values contain non-finite values.")
    if not np.isfinite(y).all():
        raise ValueError("FIT Ridge+ target Y contains non-finite values.")
    if np.any(x < -EPSILON) or np.any(x > 1.0 + EPSILON):
        raise ValueError("FIT benefit-oriented features must lie in [0, 1].")

    selected.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)

    expected_rows = EXPECTED_FIT_ROWS[n]
    expected_contexts = EXPECTED_FIT_CONTEXTS[n]
    if len(selected) != expected_rows:
        raise ValueError(f"N={n} requires {expected_rows} FIT rows; found {len(selected)}.")
    if selected["context_id"].nunique() != expected_contexts:
        raise ValueError(
            f"N={n} requires {expected_contexts} FIT context groups; "
            f"found {selected['context_id'].nunique()}."
        )
    group_sizes = selected.groupby("context_id", sort=False).size().to_numpy()
    if not np.all(group_sizes == 6):
        raise ValueError("Every FIT context must contain exactly six alternatives.")
    if selected["partition"].ne("fit").any():
        raise AssertionError("Non-FIT row entered Ridge+ estimation.")
    if selected["context_number"].gt(n).any():
        raise AssertionError("Ridge+ FIT rows escaped requested N.")
    return selected


def fit_standardized_nnls(
    x: np.ndarray,
    y: np.ndarray,
    *,
    tau: float,
) -> StandardizedNNLSFit:
    """Fit one no-intercept standardized non-negative ridge model."""
    values = np.asarray(x, dtype=float)
    target = np.asarray(y, dtype=float)
    tau_value = float(tau)

    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError("Ridge+ X must be two-dimensional with exactly 10 columns.")
    if values.shape[0] < 2:
        raise ValueError("Ridge+ requires at least two training rows.")
    if target.ndim != 1 or target.shape[0] != values.shape[0]:
        raise ValueError("Ridge+ y must be one-dimensional and aligned with X.")
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValueError("Ridge+ training arrays contain non-finite values.")
    if not np.isfinite(tau_value) or tau_value <= 0.0:
        raise ValueError("Ridge+ tau must be finite and strictly positive.")

    x_mean = np.mean(values, axis=0)
    x_sd = np.std(values, axis=0, ddof=0)
    active = x_sd > EPSILON
    x_standardized = np.zeros_like(values, dtype=float)
    if np.any(active):
        x_standardized[:, active] = (
            values[:, active] - x_mean[active]
        ) / x_sd[active]

    y_mean = float(np.mean(target))
    y_sd = float(np.std(target, ddof=0))
    y_constant = y_sd <= EPSILON

    coefficients = np.zeros(N_CRITERIA, dtype=float)
    if y_constant:
        residual_norm = 0.0
    else:
        y_standardized = (target - y_mean) / y_sd
        active_indices = np.flatnonzero(active)
        if active_indices.size == 0:
            residual_norm = float(np.linalg.norm(y_standardized))
        else:
            active_x = x_standardized[:, active_indices]
            augmented_x = np.vstack(
                [active_x, np.sqrt(tau_value) * np.eye(active_indices.size)]
            )
            augmented_y = np.concatenate(
                [y_standardized, np.zeros(active_indices.size, dtype=float)]
            )
            active_coefficients, residual_norm = nnls(augmented_x, augmented_y)
            coefficients[active_indices] = active_coefficients

    if not np.isfinite(coefficients).all() or np.any(coefficients < 0.0):
        raise FloatingPointError("Ridge+ coefficients are invalid.")
    if np.any(coefficients[~active] != 0.0):
        raise AssertionError("Zero-variance Ridge+ coefficient escaped fixed zero.")

    return StandardizedNNLSFit(
        coefficients=coefficients,
        x_mean=x_mean,
        x_sd=x_sd,
        active_feature_mask=active,
        y_mean=y_mean,
        y_sd=y_sd,
        y_constant=bool(y_constant),
        residual_norm=float(residual_norm),
        tau=tau_value,
    )


def predict_original_scale(model: StandardizedNNLSFit, x: np.ndarray) -> np.ndarray:
    """Predict after training-statistic standardization and y inverse transform."""
    values = np.asarray(x, dtype=float)
    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError("Ridge+ prediction X must have exactly 10 columns.")
    if not np.isfinite(values).all():
        raise ValueError("Ridge+ prediction X contains non-finite values.")

    standardized = np.zeros_like(values, dtype=float)
    active = model.active_feature_mask
    if np.any(active):
        standardized[:, active] = (
            values[:, active] - model.x_mean[active]
        ) / model.x_sd[active]
    prediction_standardized = standardized @ model.coefficients
    prediction = model.y_mean + model.y_sd * prediction_standardized
    if not np.isfinite(prediction).all():
        raise FloatingPointError("Ridge+ prediction became non-finite.")
    return prediction


def select_ridge_tau(
    x: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
) -> RidgeCVResult:
    """Select tau by frozen five-fold GroupKFold mean original-scale RMSE."""
    values = np.asarray(x, dtype=float)
    target = np.asarray(y, dtype=float)
    group_values = np.asarray(groups)
    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError("Ridge+ CV X must have exactly 10 columns.")
    if target.ndim != 1 or target.shape[0] != values.shape[0]:
        raise ValueError("Ridge+ CV y is not aligned with X.")
    if group_values.ndim != 1 or group_values.shape[0] != values.shape[0]:
        raise ValueError("Ridge+ CV groups are not aligned with X.")
    if not np.isfinite(values).all() or not np.isfinite(target).all():
        raise ValueError("Ridge+ CV arrays contain non-finite values.")

    unique_group_count = int(pd.Series(group_values).nunique(dropna=False))
    if unique_group_count < CV_FOLDS:
        raise ValueError("Ridge+ GroupKFold requires at least five context groups.")

    splitter = GroupKFold(n_splits=CV_FOLDS)
    splits = list(splitter.split(values, target, groups=group_values))
    fold_rmse_by_tau: dict[float, tuple[float, ...]] = {}
    mean_rmse_by_tau: dict[float, float] = {}

    for tau in CANDIDATE_TAU:
        fold_scores: list[float] = []
        for train_index, validation_index in splits:
            if set(group_values[train_index]) & set(group_values[validation_index]):
                raise AssertionError("Ridge+ context group leaked across a CV fold.")
            model = fit_standardized_nnls(
                values[train_index],
                target[train_index],
                tau=tau,
            )
            prediction = predict_original_scale(model, values[validation_index])
            rmse = float(
                np.sqrt(np.mean((target[validation_index] - prediction) ** 2))
            )
            if not np.isfinite(rmse):
                raise FloatingPointError("Ridge+ fold RMSE became non-finite.")
            fold_scores.append(rmse)
        fold_rmse_by_tau[tau] = tuple(fold_scores)
        mean_rmse_by_tau[tau] = float(np.mean(fold_scores))

    minimum_rmse = min(mean_rmse_by_tau.values())
    tied = [
        tau
        for tau in CANDIDATE_TAU
        if mean_rmse_by_tau[tau] <= minimum_rmse + TIE_ABSOLUTE_TOLERANCE
    ]
    selected_tau = float(min(tied))

    return RidgeCVResult(
        selected_tau=selected_tau,
        mean_rmse_by_tau=mean_rmse_by_tau,
        fold_rmse_by_tau=fold_rmse_by_tau,
        folds=CV_FOLDS,
        group_count=unique_group_count,
    )


def compute_ridge_plus_weights(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> RidgePlusWeightResult:
    """Fit frozen Ridge+ and return normalized non-negative coefficients."""
    selected = prepare_ridge_fit_rows(
        rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )
    x = selected.loc[:, FEATURES].to_numpy(dtype=float)
    y = selected["Y"].to_numpy(dtype=float)
    groups = selected["context_id"].to_numpy()

    cv = select_ridge_tau(x, y, groups)
    final_model = fit_standardized_nnls(x, y, tau=cv.selected_tau)
    coefficients = final_model.coefficients
    coefficient_sum = float(np.sum(coefficients))

    if coefficient_sum <= EPSILON:
        weights = np.full(N_CRITERIA, EQUAL_WEIGHT, dtype=float)
        fallback_used = True
    else:
        weights = coefficients / coefficient_sum
        fallback_used = False

    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise FloatingPointError("Ridge+ weights are invalid.")
    if not np.isclose(float(weights.sum()), 1.0, atol=EPSILON, rtol=0.0):
        raise FloatingPointError("Ridge+ weights do not sum to one.")

    weights_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, weights, strict=True)
    }
    coefficients_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, coefficients, strict=True)
    }
    zero_variance_features = tuple(
        feature
        for feature, active in zip(
            FEATURES,
            final_model.active_feature_mask,
            strict=True,
        )
        if not bool(active)
    )

    diagnostics: dict[str, Any] = {
        "method": "Ridge+",
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "partition": "fit",
        "rows_used": int(len(selected)),
        "context_groups_used": int(selected["context_id"].nunique()),
        "target": "Y",
        "coefficient_constraint": "nonnegative",
        "solver": "scipy.optimize.nnls_on_L2_augmented_design",
        "standardize_X": True,
        "standardize_y": True,
        "standardization_ddof": 0,
        "cv_statistics_fit_within_each_training_fold": True,
        "final_statistics_from_full_fit_partition": True,
        "intercept_in_standardized_space": False,
        "cv_method": "GroupKFold",
        "cv_folds": CV_FOLDS,
        "cv_shuffle": False,
        "cv_group": "context_id",
        "cv_metric": "RMSE_on_original_Y_scale",
        "selected_tau": float(cv.selected_tau),
        "tie_absolute_tolerance": TIE_ABSOLUTE_TOLERANCE,
        "tie_break": "smallest_tau",
        "y_constant": bool(final_model.y_constant),
        "coefficient_sum": coefficient_sum,
        "zero_sum_fallback": "equal_weights",
        "fallback_used": bool(fallback_used),
        "weight_rows_used": 0,
        "external_test_rows_used": 0,
        "target_Y_used": True,
        "oracle_utility_used": False,
        "shap_used": False,
        "mcdm_executed": False,
        "winner_inspected": False,
    }

    return RidgePlusWeightResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        weights_by_feature=weights_by_feature,
        coefficients_by_feature=coefficients_by_feature,
        selected_tau=float(cv.selected_tau),
        mean_cv_rmse_by_tau=dict(cv.mean_rmse_by_tau),
        fold_cv_rmse_by_tau=dict(cv.fold_rmse_by_tau),
        zero_variance_features=zero_variance_features,
        diagnostics=diagnostics,
    )
