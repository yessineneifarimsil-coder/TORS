from __future__ import annotations

"""Frozen context-block permutation-importance (PI) weighting.

PI evaluates an already-fitted XGBoost-compatible predictor on WEIGHT only.
Each criterion is permuted using the same 20 deterministic, unique context-
block derangements. The complete six-alternative criterion vector moves as a
block; other criteria remain unchanged. This module does not fit the model,
use external TEST, run SHAP/MCDM, inspect winners, or write result files.
"""

from dataclasses import dataclass
import hashlib
from typing import Any

import numpy as np
import pandas as pd


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
ALTERNATIVES_PER_CONTEXT = 6
MASTER_SEED = 84001
REPEATS = 20
MAX_CANDIDATE_DRAWS = 100000
SD_DDOF = 1
EQUAL_WEIGHT = 0.1

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_WEIGHT_ROWS = {25: 30, 50: 60, 100: 120, 250: 300, 1000: 1200}
EXPECTED_WEIGHT_CONTEXTS = {25: 5, 50: 10, 100: 20, 250: 50, 1000: 200}
SORT_COLUMNS = ("context_number", "alternative_id")


class PermutationImportanceNumericalError(RuntimeError):
    """Raised when a fitted predictor returns invalid PI predictions."""


@dataclass(frozen=True)
class ContextDerangementPlan:
    replication_seed: int
    n_contexts: int
    context_count: int
    permutations: tuple[tuple[int, ...], ...]
    candidate_draws: int
    identity_sha256: str


@dataclass(frozen=True)
class PermutationImportanceWeightResult:
    replication_seed: int
    n_contexts: int
    baseline_mse: float
    repeat_importance_by_feature: dict[str, tuple[float, ...]]
    mean_importance_by_feature: dict[str, float]
    sd_importance_by_feature: dict[str, float]
    nonnegative_importance_by_feature: dict[str, float]
    weights_by_feature: dict[str, float]
    fallback_used: bool
    derangement_plan: ContextDerangementPlan
    diagnostics: dict[str, Any]


def prepare_pi_weight_rows(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> pd.DataFrame:
    """Return exact nested WEIGHT rows in frozen deterministic order."""
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
        raise ValueError(f"PI input is missing columns: {missing}.")
    if rows.empty:
        raise ValueError("PI input must not be empty.")

    nested = rows.loc[rows["context_number"].le(n)].copy()
    if nested.empty:
        raise ValueError("No nested estimation rows found for requested N.")
    unexpected_partitions = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected_partitions:
        raise ValueError(
            "Unexpected partition labels inside nested estimation scope: "
            f"{unexpected_partitions}."
        )

    # Frozen WEIGHT-only firewall. FIT values are excluded before scientific
    # feature/target/seed validation; the fitted model is supplied separately.
    selected = nested.loc[nested["partition"].eq("weight")].copy()
    if selected.empty:
        raise ValueError("No WEIGHT rows found for requested N.")
    if selected["replication_seed"].isna().any():
        raise ValueError("WEIGHT replication_seed contains missing values.")
    observed_seeds = set(selected["replication_seed"].astype(int).tolist())
    if observed_seeds != {int(replication_seed)}:
        raise ValueError(
            f"PI WEIGHT rows must contain exactly replication_seed={replication_seed}; "
            f"found {sorted(observed_seeds)}."
        )
    if selected.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate WEIGHT context-alternative rows detected.")

    x = selected.loc[:, FEATURES].to_numpy(dtype=float)
    y = selected["Y"].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("WEIGHT PI feature values contain non-finite values.")
    if not np.isfinite(y).all():
        raise ValueError("WEIGHT PI target Y contains non-finite values.")
    if np.any(x < -1.0e-12) or np.any(x > 1.0 + 1.0e-12):
        raise ValueError("WEIGHT benefit-oriented features must lie in [0, 1].")

    selected.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)

    expected_rows = EXPECTED_WEIGHT_ROWS[n]
    expected_contexts = EXPECTED_WEIGHT_CONTEXTS[n]
    if len(selected) != expected_rows:
        raise ValueError(f"N={n} requires {expected_rows} WEIGHT rows; found {len(selected)}.")
    if selected["context_id"].nunique() != expected_contexts:
        raise ValueError(
            f"N={n} requires {expected_contexts} WEIGHT context groups; "
            f"found {selected['context_id'].nunique()}."
        )
    if selected["context_number"].nunique() != expected_contexts:
        raise ValueError("WEIGHT context_number count does not match context groups.")
    if selected.groupby("context_id")["context_number"].nunique().max() != 1:
        raise ValueError("A WEIGHT context_id maps to multiple context numbers.")
    if selected.groupby("context_number")["context_id"].nunique().max() != 1:
        raise ValueError("A WEIGHT context number maps to multiple context_ids.")
    group_sizes = selected.groupby("context_number", sort=False).size().to_numpy()
    if not np.all(group_sizes == ALTERNATIVES_PER_CONTEXT):
        raise ValueError("Every WEIGHT context must contain exactly six alternatives.")
    if selected["partition"].ne("weight").any():
        raise AssertionError("Non-WEIGHT row entered PI evaluation.")
    if selected["context_number"].gt(n).any():
        raise AssertionError("PI WEIGHT rows escaped requested N.")
    return selected


def generate_context_derangements(
    *,
    replication_seed: int,
    n_contexts: int,
    context_count: int,
) -> ContextDerangementPlan:
    """Generate the frozen 20 unique derangements for one replication and N."""
    n = int(n_contexts)
    m = int(context_count)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level.")
    if m != EXPECTED_WEIGHT_CONTEXTS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_WEIGHT_CONTEXTS[n]} WEIGHT contexts; found {m}."
        )

    seed_sequence = np.random.SeedSequence(
        [int(replication_seed), MASTER_SEED, n]
    )
    rng = np.random.default_rng(seed_sequence)
    accepted: list[tuple[int, ...]] = []
    seen: set[tuple[int, ...]] = set()
    candidate_draws = 0
    positions = np.arange(m)
    while len(accepted) < REPEATS and candidate_draws < MAX_CANDIDATE_DRAWS:
        candidate_draws += 1
        permutation = rng.permutation(m)
        key = tuple(int(value) for value in permutation.tolist())
        if np.any(permutation == positions) or key in seen:
            continue
        seen.add(key)
        accepted.append(key)

    if len(accepted) != REPEATS:
        raise RuntimeError(
            "Could not generate 20 unique context-block derangements within "
            "100000 candidate draws; no PI result is permitted."
        )
    payload = "\n".join(",".join(str(value) for value in item) for item in accepted)
    identity_sha256 = hashlib.sha256(payload.encode("ascii")).hexdigest()
    return ContextDerangementPlan(
        replication_seed=int(replication_seed),
        n_contexts=n,
        context_count=m,
        permutations=tuple(accepted),
        candidate_draws=candidate_draws,
        identity_sha256=identity_sha256,
    )


def permute_context_feature_blocks(
    x: np.ndarray,
    *,
    feature_index: int,
    permutation: tuple[int, ...],
    context_count: int,
) -> np.ndarray:
    """Copy source blocks to destinations for one criterion and derangement."""
    values = np.asarray(x, dtype=float)
    m = int(context_count)
    j = int(feature_index)
    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError("PI feature matrix must be two-dimensional with 10 columns.")
    if values.shape[0] != m * ALTERNATIVES_PER_CONTEXT:
        raise ValueError("PI feature rows do not form complete six-alternative blocks.")
    if not 0 <= j < N_CRITERIA:
        raise ValueError("PI feature index is outside 0..9.")
    if len(permutation) != m or set(permutation) != set(range(m)):
        raise ValueError("PI context-block permutation is invalid.")
    if any(source == destination for destination, source in enumerate(permutation)):
        raise ValueError("PI context-block permutation must be a derangement.")

    result = values.copy()
    blocks = values[:, j].reshape(m, ALTERNATIVES_PER_CONTEXT)
    result[:, j] = blocks[np.asarray(permutation, dtype=int)].reshape(-1)
    return result


def normalize_pi_importances(
    mean_importances: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, bool]:
    """Truncate negative means and apply the frozen all-nonpositive fallback."""
    means = np.asarray(mean_importances, dtype=float)
    if means.shape != (N_CRITERIA,) or not np.isfinite(means).all():
        raise ValueError("PI mean importances must be ten finite values.")
    nonnegative = np.maximum(means, 0.0)
    if not np.any(means > 0.0):
        return nonnegative, np.full(N_CRITERIA, EQUAL_WEIGHT), True
    total = float(np.sum(nonnegative))
    if not np.isfinite(total) or total <= 0.0:
        raise FloatingPointError("Positive PI importance total is invalid.")
    weights = nonnegative / total
    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise FloatingPointError("PI weights are invalid.")
    if not np.isclose(float(np.sum(weights)), 1.0, atol=1.0e-12, rtol=0.0):
        raise FloatingPointError("PI weights do not sum to one.")
    return nonnegative, weights, False


def _predict(fitted_model: Any, x: np.ndarray) -> np.ndarray:
    predict = getattr(fitted_model, "predict", None)
    if not callable(predict):
        raise TypeError("PI requires an already-fitted model with callable predict(X).")
    prediction = np.asarray(predict(x), dtype=float)
    if prediction.size != len(x):
        raise PermutationImportanceNumericalError(
            f"PI model returned {prediction.size} predictions for {len(x)} rows."
        )
    prediction = prediction.reshape(-1)
    if not np.isfinite(prediction).all():
        raise PermutationImportanceNumericalError(
            "PI model predictions contain non-finite values."
        )
    return prediction


def compute_permutation_importance_weights(
    rows: pd.DataFrame,
    *,
    fitted_model: Any,
    replication_seed: int,
    n_contexts: int,
) -> PermutationImportanceWeightResult:
    """Compute frozen WEIGHT-MSE context-block PI from a fitted predictor."""
    selected = prepare_pi_weight_rows(
        rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )
    x = selected.loc[:, FEATURES].to_numpy(dtype=float)
    y = selected["Y"].to_numpy(dtype=float)
    context_numbers = tuple(
        int(value) for value in selected["context_number"].drop_duplicates().tolist()
    )
    plan = generate_context_derangements(
        replication_seed=replication_seed,
        n_contexts=n_contexts,
        context_count=len(context_numbers),
    )

    baseline_prediction = _predict(fitted_model, x)
    baseline_mse = float(np.mean((y - baseline_prediction) ** 2))
    if not np.isfinite(baseline_mse):
        raise PermutationImportanceNumericalError("PI baseline MSE is non-finite.")

    repeat_matrix = np.empty((N_CRITERIA, REPEATS), dtype=float)
    for feature_index in range(N_CRITERIA):
        for repeat_index, permutation in enumerate(plan.permutations):
            permuted_x = permute_context_feature_blocks(
                x,
                feature_index=feature_index,
                permutation=permutation,
                context_count=plan.context_count,
            )
            prediction = _predict(fitted_model, permuted_x)
            permuted_mse = float(np.mean((y - prediction) ** 2))
            repeat_matrix[feature_index, repeat_index] = permuted_mse - baseline_mse

    if not np.isfinite(repeat_matrix).all():
        raise PermutationImportanceNumericalError(
            "PI repeat importances contain non-finite values."
        )
    means = np.mean(repeat_matrix, axis=1)
    standard_deviations = np.std(repeat_matrix, axis=1, ddof=SD_DDOF)
    nonnegative, weights, fallback_used = normalize_pi_importances(means)

    repeat_importance_by_feature = {
        feature: tuple(float(value) for value in repeat_matrix[index])
        for index, feature in enumerate(FEATURES)
    }
    mean_importance_by_feature = {
        feature: float(value) for feature, value in zip(FEATURES, means, strict=True)
    }
    sd_importance_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, standard_deviations, strict=True)
    }
    nonnegative_importance_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, nonnegative, strict=True)
    }
    weights_by_feature = {
        feature: float(value) for feature, value in zip(FEATURES, weights, strict=True)
    }

    diagnostics: dict[str, Any] = {
        "method": "PermutationImportance",
        "model": "already_fitted_xgboost_compatible_predictor",
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "evaluation_partition": "weight",
        "weight_rows_used": int(len(selected)),
        "weight_contexts_used": int(plan.context_count),
        "target": "Y",
        "loss": "mean_squared_error",
        "importance_per_repeat": "permuted_MSE_minus_baseline_MSE",
        "repeats": REPEATS,
        "sd_ddof": SD_DDOF,
        "permutation_unit": "context_block_six_alternatives",
        "permutation_scheme": "derangement",
        "master_seed": MASTER_SEED,
        "rng_seed_sequence": [int(replication_seed), MASTER_SEED, int(n_contexts)],
        "candidate_draws": int(plan.candidate_draws),
        "derangement_identity_sha256": plan.identity_sha256,
        "context_order": "context_number_ascending",
        "alternative_order_within_block": "alternative_id_ascending",
        "mapping_direction": "destination_d_copies_source_perm_d",
        "same_20_derangements_reused_across_all_criteria": True,
        "reuse_across_rho_c_lambda": True,
        "negative_mean_importance_rule": "truncate_to_zero",
        "normalization": "divide_nonnegative_mean_importance_by_sum",
        "all_nonpositive_fallback": "equal_weights",
        "fallback_used": bool(fallback_used),
        "model_fit_executed_by_pi": False,
        "fit_rows_used_for_pi_evaluation": 0,
        "external_test_rows_used": 0,
        "target_Y_used": True,
        "oracle_utility_used": False,
        "shap_used": False,
        "mcdm_executed": False,
        "winner_inspected": False,
    }
    return PermutationImportanceWeightResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        baseline_mse=baseline_mse,
        repeat_importance_by_feature=repeat_importance_by_feature,
        mean_importance_by_feature=mean_importance_by_feature,
        sd_importance_by_feature=sd_importance_by_feature,
        nonnegative_importance_by_feature=nonnegative_importance_by_feature,
        weights_by_feature=weights_by_feature,
        fallback_used=bool(fallback_used),
        derangement_plan=plan,
        diagnostics=diagnostics,
    )
