from __future__ import annotations

"""Frozen CRITIC weighting implementation.

Primary estimation uses WEIGHT only. The prespecified robustness variant uses
FIT+WEIGHT. Inputs are benefit-oriented g_C1..g_C10 values. External TEST rows,
Y, oracle utility, SHAP values, MCDM scores, and winner identities are not used.
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
class CriticCoreResult:
    weights: np.ndarray
    information: np.ndarray
    standard_deviation: np.ndarray
    constant_mask: np.ndarray
    fallback_used: bool


@dataclass(frozen=True)
class CriticWeightResult:
    replication_seed: int
    n_contexts: int
    partition_scope: str
    weights_by_feature: dict[str, float]
    information_by_feature: dict[str, float]
    standard_deviation_by_feature: dict[str, float]
    constant_features: tuple[str, ...]
    diagnostics: dict[str, Any]


def _validate_scope(partition_scope: str) -> PartitionScope:
    scope = str(partition_scope)
    if scope not in {"weight", "fit_plus_weight"}:
        raise ValueError(
            "partition_scope must be 'weight' or 'fit_plus_weight'."
        )
    return scope  # type: ignore[return-value]


def prepare_critic_rows(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    partition_scope: PartitionScope = "weight",
) -> pd.DataFrame:
    """Return the frozen CRITIC estimation rows in deterministic order."""
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
        raise ValueError(f"CRITIC input is missing columns: {missing}.")
    if rows.empty:
        raise ValueError("CRITIC input must not be empty.")

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
            f"Nested CRITIC rows must contain exactly replication_seed={replication_seed}; "
            f"found {sorted(observed_seeds)}."
        )

    if nested.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate nested context-alternative rows detected.")

    unexpected_partitions = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected_partitions:
        raise ValueError(
            f"Unexpected partition labels inside nested estimation scope: "
            f"{unexpected_partitions}."
        )

    g_nested = nested.loc[:, FEATURES].to_numpy(dtype=float)
    if not np.isfinite(g_nested).all():
        raise ValueError("Nested CRITIC feature values contain non-finite values.")
    if np.any(g_nested < -EPSILON) or np.any(g_nested > 1.0 + EPSILON):
        raise ValueError("Nested CRITIC benefit-oriented features must lie in [0, 1].")

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
        raise AssertionError("Non-WEIGHT row entered primary CRITIC estimation.")
    if scope == "fit_plus_weight" and not set(selected["partition"]) <= {"fit", "weight"}:
        raise AssertionError("Unexpected row entered CRITIC robustness estimation.")
    if selected["context_number"].gt(n).any():
        raise AssertionError("CRITIC estimation rows escaped requested N.")

    return selected


def compute_critic_from_matrix(matrix: np.ndarray) -> CriticCoreResult:
    """Compute frozen CRITIC weights from an n-by-10 benefit-oriented matrix."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or values.shape[1] != N_CRITERIA:
        raise ValueError("CRITIC matrix must be two-dimensional with exactly 10 columns.")
    if values.shape[0] == 0:
        raise ValueError("CRITIC matrix must contain at least one row.")
    if not np.isfinite(values).all():
        raise ValueError("CRITIC matrix contains non-finite values.")

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

    standard_deviation = np.std(normalized, axis=0, ddof=0)
    standard_deviation[constant_mask] = 0.0

    information = np.zeros(N_CRITERIA, dtype=float)
    if nonconstant.size:
        centered = normalized[:, nonconstant] - np.mean(
            normalized[:, nonconstant],
            axis=0,
        )
        norms = np.sqrt(np.sum(centered * centered, axis=0))
        if np.any(norms <= 0.0):
            raise FloatingPointError(
                "Nonconstant CRITIC column produced zero centered norm."
            )

        correlation = (centered.T @ centered) / np.outer(norms, norms)
        if not np.isfinite(correlation).all():
            raise FloatingPointError("CRITIC correlation matrix is non-finite.")

        # Theoretical Pearson correlations lie in [-1, 1]. Permit only
        # machine-roundoff excursions before restoring the mathematical bound.
        if np.any(correlation < -1.0 - EPSILON) or np.any(correlation > 1.0 + EPSILON):
            raise FloatingPointError("CRITIC Pearson correlation escaped [-1, 1].")
        correlation = np.clip(correlation, -1.0, 1.0)

        conflict = np.sum(1.0 - correlation, axis=1)
        information[nonconstant] = standard_deviation[nonconstant] * conflict

    if np.any(information < -EPSILON):
        raise FloatingPointError("CRITIC information became materially negative.")
    information = np.maximum(information, 0.0)

    total_information = float(np.sum(information))
    if total_information <= EPSILON:
        weights = np.full(N_CRITERIA, EQUAL_WEIGHT, dtype=float)
        fallback_used = True
    else:
        weights = information / total_information
        fallback_used = False

    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise FloatingPointError("CRITIC weights are invalid.")
    if not np.isclose(float(weights.sum()), 1.0, atol=EPSILON, rtol=0.0):
        raise FloatingPointError("CRITIC weights do not sum to one.")

    return CriticCoreResult(
        weights=weights,
        information=information,
        standard_deviation=standard_deviation,
        constant_mask=constant_mask,
        fallback_used=fallback_used,
    )


def compute_critic_weights(
    rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    partition_scope: PartitionScope = "weight",
) -> CriticWeightResult:
    """Compute frozen CRITIC weights for one benchmark instance."""
    scope = _validate_scope(partition_scope)
    selected = prepare_critic_rows(
        rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
        partition_scope=scope,
    )
    matrix = selected.loc[:, FEATURES].to_numpy(dtype=float)
    core = compute_critic_from_matrix(matrix)

    weights_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, core.weights, strict=True)
    }
    information_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, core.information, strict=True)
    }
    standard_deviation_by_feature = {
        feature: float(value)
        for feature, value in zip(
            FEATURES,
            core.standard_deviation,
            strict=True,
        )
    }
    constant_features = tuple(
        feature
        for feature, is_constant in zip(FEATURES, core.constant_mask, strict=True)
        if bool(is_constant)
    )

    diagnostics: dict[str, Any] = {
        "method": "CRITIC",
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "partition_scope": scope,
        "rows_used": int(len(selected)),
        "preprocessing": "criterionwise_minmax",
        "minmax_epsilon": EPSILON,
        "standard_deviation_ddof": 0,
        "correlation": "Pearson_on_nonconstant_normalized_columns",
        "constant_range_rule": "range_lt_epsilon",
        "constant_columns_excluded_from_conflict_sum": True,
        "all_zero_information_fallback": "equal_weights",
        "fallback_used": bool(core.fallback_used),
        "external_test_rows_used": 0,
        "target_Y_used": False,
        "oracle_utility_used": False,
        "shap_used": False,
        "mcdm_executed": False,
        "winner_inspected": False,
    }

    return CriticWeightResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        partition_scope=scope,
        weights_by_feature=weights_by_feature,
        information_by_feature=information_by_feature,
        standard_deviation_by_feature=standard_deviation_by_feature,
        constant_features=constant_features,
        diagnostics=diagnostics,
    )
