from __future__ import annotations

"""Frozen Entropy weighting implementation.

Primary estimation uses WEIGHT only. The prespecified robustness variant uses
FIT+WEIGHT. Inputs are benefit-oriented g_C1..g_C10 values. External TEST rows,
Y, oracle utility, SHAP values, MCDM scores, and winner identities are not used.

The frozen method is explicitly min-max-then-Shannon: criterionwise min-max
preprocessing is followed by Shannon entropy over alternative-context rows.
"""

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import pandas as pd


FEATURES = tuple(f"g_C{i}" for i in range(1, 11))
N_CRITERIA = 10
EPSILON = 1.0e-12
EQUAL_WEIGHT = 0.1

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_WEIGHT_ROWS = {25: 30, 50: 60, 100: 120, 250: 300, 1000: 1200}
EXPECTED_FIT_PLUS_WEIGHT_ROWS = {
    25: 150,
    50: 300,
    100: 600,
    250: 1500,
    1000: 6000,
}
SORT_COLUMNS = ("context_number", "alternative_id")
PartitionScope = Literal["weight", "fit_plus_weight"]


@dataclass(frozen=True)
class EntropyCoreResult:
    weights: np.ndarray
    entropy: np.ndarray
    diversification: np.ndarray
    normalized_column_sum: np.ndarray
    constant_mask: np.ndarray
    zero_information_mask: np.ndarray
    fallback_used: bool


@dataclass(frozen=True)
class EntropyWeightResult:
    replication_seed: int
    n_contexts: int
    partition_scope: str
    weights_by_feature: dict[str, float]
    entropy_by_feature: dict[str, float]
    diversification_by_feature: dict[str, float]
    normalized_column_sum_by_feature: dict[str, float]
    constant_features: tuple[str, ...]
    zero_information_features: tuple[str, ...]
    diagnostics: dict[str, Any]


def _validate_scope(partition_scope: str) -> PartitionScope:
    scope = str(partition_scope)
    if scope not in {"weight", "fit_plus_weight"}:
        raise ValueError(
            "partition_scope must be 'weight' or 'fit_plus_weight'."
        )
    return scope  # type: ignore[return-value]


def prepare_entropy_rows(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    partition_scope: PartitionScope = "weight",
) -> pd.DataFrame:
    """Return the frozen Entropy estimation rows in deterministic order."""
    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")
    scope = _validate_scope(partition_scope)

    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        *FEATURES,
    }
    missing = sorted(required - set(rows.columns))
    if missing:
        raise ValueError(f"Entropy input is missing columns: {missing}.")
    if rows.empty:
        raise ValueError("Entropy input must not be empty.")

    # Frozen TEST firewall: restrict to the nested estimation scope before
    # validating scientific values, identities, duplicates, or partitions.
    nested = rows.loc[rows["context_number"].le(n)].copy()
    if nested.empty:
        raise ValueError("No nested estimation rows found for requested N.")

    if nested["replication_seed"].isna().any():
        raise ValueError("Nested estimation replication_seed contains missing values.")
    observed_seeds = set(nested["replication_seed"].astype(int).tolist())
    if observed_seeds != {int(replication_seed)}:
        raise ValueError(
            f"Nested Entropy rows must contain exactly replication_seed={replication_seed}; "
            f"found {sorted(observed_seeds)}."
        )

    if nested.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate nested context-alternative rows detected.")

    unexpected_partitions = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected_partitions:
        raise ValueError(
            "Unexpected partition labels inside nested estimation scope: "
            f"{unexpected_partitions}."
        )

    g_nested = nested.loc[:, FEATURES].to_numpy(dtype=float)
    if not np.isfinite(g_nested).all():
        raise ValueError("Nested Entropy feature values contain non-finite values.")
    if np.any(g_nested < -EPSILON) or np.any(g_nested > 1.0 + EPSILON):
        raise ValueError(
            "Nested Entropy benefit-oriented features must lie in [0, 1]."
        )

    if scope == "weight":
        selected = nested.loc[nested["partition"].eq("weight")].copy()
        expected_rows = EXPECTED_WEIGHT_ROWS[n]
    else:
        selected = nested.loc[nested["partition"].isin(("fit", "weight"))].copy()
        expected_rows = EXPECTED_FIT_PLUS_WEIGHT_ROWS[n]

    selected.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    selected.reset_index(drop=True, inplace=True)

    if len(selected) != expected_rows:
        raise ValueError(
            f"N={n}, scope={scope} requires {expected_rows} rows; "
            f"found {len(selected)}."
        )

    if scope == "weight" and selected["partition"].ne("weight").any():
        raise AssertionError("Non-WEIGHT row entered primary Entropy estimation.")
    if scope == "fit_plus_weight" and not set(selected["partition"]) <= {
        "fit",
        "weight",
    }:
        raise AssertionError("Unexpected row entered Entropy robustness estimation.")
    if selected["context_number"].gt(n).any():
        raise AssertionError("Entropy estimation rows escaped requested N.")

    return selected


def compute_entropy_from_matrix(matrix: np.ndarray) -> EntropyCoreResult:
    """Compute frozen min-max-then-Shannon weights from an n-by-10 matrix."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError(
            "Entropy matrix must be two-dimensional with exactly 10 columns."
        )
    if values.shape[0] < 2:
        raise ValueError("Entropy matrix must contain at least two rows.")
    if not np.isfinite(values).all():
        raise ValueError("Entropy matrix contains non-finite values.")

    n_rows = int(values.shape[0])
    minimum = np.min(values, axis=0)
    maximum = np.max(values, axis=0)
    ranges = maximum - minimum
    constant_mask = ranges < EPSILON

    normalized = np.zeros_like(values, dtype=float)
    nonconstant = np.flatnonzero(~constant_mask)
    if nonconstant.size:
        normalized[:, nonconstant] = (
            values[:, nonconstant] - minimum[nonconstant]
        ) / (ranges[nonconstant] + EPSILON)

    normalized_column_sum = np.sum(normalized, axis=0)
    zero_information_mask = constant_mask | (
        normalized_column_sum <= EPSILON
    )

    # Setting e_j=1 for zero-information columns makes d_j=0 explicit.
    entropy = np.ones(N_CRITERIA, dtype=float)
    log_n = float(np.log(n_rows))
    informative = np.flatnonzero(~zero_information_mask)

    for j in informative:
        probabilities = normalized[:, j] / normalized_column_sum[j]
        if not np.isfinite(probabilities).all():
            raise FloatingPointError(
                "Entropy probability vector contains non-finite values."
            )
        if np.any(probabilities < -EPSILON):
            raise FloatingPointError("Entropy probability became negative.")
        probabilities = np.maximum(probabilities, 0.0)

        positive = probabilities > 0.0
        # Frozen mathematical convention: 0 * log(0) contributes exactly zero.
        entropy_j = -float(
            np.sum(probabilities[positive] * np.log(probabilities[positive]))
        ) / log_n
        if entropy_j < -EPSILON or entropy_j > 1.0 + EPSILON:
            raise FloatingPointError("Shannon entropy escaped [0, 1].")
        entropy[j] = float(np.clip(entropy_j, 0.0, 1.0))

    diversification = 1.0 - entropy
    diversification[zero_information_mask] = 0.0
    if np.any(diversification < -EPSILON):
        raise FloatingPointError("Entropy diversification became negative.")
    diversification = np.maximum(diversification, 0.0)

    total_diversification = float(np.sum(diversification))
    if total_diversification <= EPSILON:
        weights = np.full(N_CRITERIA, EQUAL_WEIGHT, dtype=float)
        fallback_used = True
    else:
        weights = diversification / total_diversification
        fallback_used = False

    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise FloatingPointError("Entropy weights are invalid.")
    if not np.isclose(float(weights.sum()), 1.0, atol=EPSILON, rtol=0.0):
        raise FloatingPointError("Entropy weights do not sum to one.")

    return EntropyCoreResult(
        weights=weights,
        entropy=entropy,
        diversification=diversification,
        normalized_column_sum=normalized_column_sum,
        constant_mask=constant_mask,
        zero_information_mask=zero_information_mask,
        fallback_used=fallback_used,
    )


def compute_entropy_weights(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    partition_scope: PartitionScope = "weight",
) -> EntropyWeightResult:
    """Compute frozen Entropy weights for one benchmark instance."""
    scope = _validate_scope(partition_scope)
    selected = prepare_entropy_rows(
        rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
        partition_scope=scope,
    )
    matrix = selected.loc[:, FEATURES].to_numpy(dtype=float)
    core = compute_entropy_from_matrix(matrix)

    weights_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, core.weights, strict=True)
    }
    entropy_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, core.entropy, strict=True)
    }
    diversification_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, core.diversification, strict=True)
    }
    normalized_column_sum_by_feature = {
        feature: float(value)
        for feature, value in zip(
            FEATURES,
            core.normalized_column_sum,
            strict=True,
        )
    }
    constant_features = tuple(
        feature
        for feature, is_constant in zip(
            FEATURES,
            core.constant_mask,
            strict=True,
        )
        if bool(is_constant)
    )
    zero_information_features = tuple(
        feature
        for feature, is_zero in zip(
            FEATURES,
            core.zero_information_mask,
            strict=True,
        )
        if bool(is_zero)
    )

    diagnostics: dict[str, Any] = {
        "method": "Entropy",
        "variant": "minmax_then_Shannon",
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "partition_scope": scope,
        "rows_used": int(len(selected)),
        "n_definition": "number_of_alternative_context_rows_in_selected_partition",
        "preprocessing": "criterionwise_minmax",
        "minmax_epsilon": EPSILON,
        "constant_range_rule": "range_lt_epsilon",
        "zero_column_sum_rule": "diversification_zero_if_sum_le_epsilon",
        "zero_log_zero": True,
        "entropy_log_base": "natural_log_ratio_base_invariant",
        "all_zero_diversification_fallback": "equal_weights",
        "fallback_used": bool(core.fallback_used),
        "external_test_rows_used": 0,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "shap_used": False,
        "mcdm_executed": False,
        "winner_inspected": False,
    }

    return EntropyWeightResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        partition_scope=scope,
        weights_by_feature=weights_by_feature,
        entropy_by_feature=entropy_by_feature,
        diversification_by_feature=diversification_by_feature,
        normalized_column_sum_by_feature=normalized_column_sum_by_feature,
        constant_features=constant_features,
        zero_information_features=zero_information_features,
        diagnostics=diagnostics,
    )
