from __future__ import annotations

"""Closed-form oracle interventional Shapley attribution weights.

Production implementation of the frozen oracle-attribution protocol:

FIT background moments -> closed-form local oracle Shapley values on WEIGHT
-> mean absolute attribution -> normalized global oracle attribution weights.

The module consumes q_C1..q_C10 values already produced by the frozen oracle
utility implementation. It does not recompute q(g), use Y, inspect external
TEST for weight estimation, fit a predictive model, call SHAP, run MCDM, or
select an ITS winner.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


CRITERIA = tuple(f"C{i}" for i in range(1, 11))
FEATURES = tuple(f"g_{criterion}" for criterion in CRITERIA)
Q_COLUMNS = tuple(f"q_{criterion}" for criterion in CRITERIA)
SORT_COLUMNS = ("context_number", "alternative_id")

ALLOWED_N = (25, 50, 100, 250, 1000)
EXPECTED_FIT_ROWS = {25: 120, 50: 240, 100: 480, 250: 1200, 1000: 4800}
EXPECTED_WEIGHT_ROWS = {25: 30, 50: 60, 100: 120, 250: 300, 1000: 1200}

NUMERICAL_TOL = 1.0e-12
IMPORTANCE_EPSILON = 1.0e-12
CLOSED_FORM_VALIDATION_TOL = 1.0e-10
ALLOWED_LAMBDAS = (0.0, 0.5, 1.0)


@dataclass(frozen=True)
class OracleBackgroundMoments:
    marginal_by_criterion: dict[str, float]
    joint_by_pair: dict[str, float]


@dataclass(frozen=True)
class OracleAttributionResult:
    replication_seed: int
    n_contexts: int
    lambda_value: float
    weights_defined: bool
    importance_by_feature: dict[str, float]
    weights_by_feature: dict[str, float] | None
    background_moments: OracleBackgroundMoments
    diagnostics: dict[str, Any]


def _pair_key(left: str, right: str) -> str:
    a, b = sorted((str(left), str(right)))
    return f"{a}|{b}"


def _validated_lambda(lambda_value: float) -> float:
    lam = float(lambda_value)
    if not np.isfinite(lam):
        raise ValueError("lambda must be finite.")
    if not any(abs(lam - allowed) <= NUMERICAL_TOL for allowed in ALLOWED_LAMBDAS):
        raise ValueError(
            f"lambda={lam} is not one of the frozen levels {list(ALLOWED_LAMBDAS)}."
        )
    return lam


def _validated_spec(oracle_spec: Any) -> tuple[np.ndarray, tuple[Any, ...]]:
    try:
        alphas_raw = oracle_spec.alphas
        interactions = tuple(oracle_spec.interactions)
    except AttributeError as exc:
        raise ValueError("oracle_spec must expose alphas and interactions.") from exc

    if set(alphas_raw) != set(CRITERIA):
        raise ValueError("Oracle alpha mapping must contain exactly C1..C10.")

    alpha = np.asarray([float(alphas_raw[c]) for c in CRITERIA], dtype=float)
    if not np.isfinite(alpha).all() or np.any(alpha < 0.0):
        raise ValueError("Oracle alpha coefficients must be finite and nonnegative.")
    if not np.isclose(float(alpha.sum()), 1.0, atol=NUMERICAL_TOL, rtol=0.0):
        raise ValueError("Oracle alpha coefficients must sum to one.")

    if not interactions:
        raise ValueError("Oracle interaction graph must not be empty.")

    seen: set[str] = set()
    beta_values: list[float] = []
    for edge in interactions:
        try:
            left = str(edge.left)
            right = str(edge.right)
            beta = float(edge.beta)
        except AttributeError as exc:
            raise ValueError("Every interaction must expose left, right, and beta.") from exc

        if left not in CRITERIA or right not in CRITERIA or left == right:
            raise ValueError(f"Invalid oracle interaction edge: {(left, right)}.")

        key = _pair_key(left, right)
        if key in seen:
            raise ValueError(f"Duplicate oracle interaction edge: {key}.")
        seen.add(key)

        if not np.isfinite(beta) or beta < 0.0:
            raise ValueError("Oracle interaction coefficients must be finite and nonnegative.")
        beta_values.append(beta)

    if not np.isclose(float(sum(beta_values)), 1.0, atol=NUMERICAL_TOL, rtol=0.0):
        raise ValueError("Oracle interaction coefficients must sum to one.")

    return alpha, interactions


def prepare_oracle_attribution_rows(
    oracle_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return stable FIT-background and WEIGHT-evaluation rows for one frozen N."""
    n = int(n_contexts)
    if n not in ALLOWED_N:
        raise ValueError(f"N={n} is not a frozen sample-size level: {list(ALLOWED_N)}.")

    required = {
        "context_id",
        "context_number",
        "replication_seed",
        "partition",
        "alternative_id",
        *Q_COLUMNS,
    }
    missing = sorted(required - set(oracle_rows.columns))
    if missing:
        raise ValueError(f"Oracle attribution input is missing columns: {missing}.")

    if oracle_rows.empty:
        raise ValueError("Oracle attribution input must not be empty.")

    # Frozen TEST firewall: restrict to the nested estimation scope before
    # validating scientific values, identities, or duplicates. External TEST
    # rows therefore cannot alter whether oracle weights are defined.
    nested = oracle_rows.loc[oracle_rows["context_number"].le(n)].copy()
    if nested.empty:
        raise ValueError("No nested estimation rows found for requested N.")

    if nested["replication_seed"].isna().any():
        raise ValueError("Nested estimation replication_seed contains missing values.")

    observed_seeds = set(nested["replication_seed"].astype(int).tolist())
    if observed_seeds != {int(replication_seed)}:
        raise ValueError(
            f"Nested oracle-attribution rows must contain exactly "
            f"replication_seed={replication_seed}; found {sorted(observed_seeds)}."
        )

    if nested.duplicated(["context_id", "alternative_id"]).any():
        raise ValueError("Duplicate nested context-alternative rows detected.")

    unexpected_partitions = sorted(set(nested["partition"]) - {"fit", "weight"})
    if unexpected_partitions:
        raise ValueError(
            f"Unexpected partition labels inside nested estimation scope: "
            f"{unexpected_partitions}."
        )

    q_nested = nested.loc[:, Q_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(q_nested).all():
        raise ValueError("Nested oracle q-values contain non-finite values.")
    if np.any(q_nested < -NUMERICAL_TOL) or np.any(q_nested > 1.0 + NUMERICAL_TOL):
        raise ValueError("Nested oracle q-values must lie in [0, 1].")

    fit = nested.loc[nested["partition"].eq("fit")].copy()
    weight = nested.loc[nested["partition"].eq("weight")].copy()

    fit.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    weight.sort_values(list(SORT_COLUMNS), kind="stable", inplace=True)
    fit.reset_index(drop=True, inplace=True)
    weight.reset_index(drop=True, inplace=True)

    if len(fit) != EXPECTED_FIT_ROWS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_FIT_ROWS[n]} FIT rows; found {len(fit)}."
        )
    if len(weight) != EXPECTED_WEIGHT_ROWS[n]:
        raise ValueError(
            f"N={n} requires {EXPECTED_WEIGHT_ROWS[n]} WEIGHT rows; found {len(weight)}."
        )
    if fit["partition"].ne("fit").any():
        raise AssertionError("Non-FIT row entered oracle background moments.")
    if weight["partition"].ne("weight").any():
        raise AssertionError("Non-WEIGHT row entered oracle attribution evaluation.")
    if fit["context_number"].gt(n).any() or weight["context_number"].gt(n).any():
        raise AssertionError("Nested oracle-attribution rows escaped requested N.")

    return fit, weight


def compute_fit_background_moments(
    fit_rows: pd.DataFrame,
    *,
    oracle_spec: Any,
) -> OracleBackgroundMoments:
    """Compute frozen FIT marginal and same-row joint q moments."""
    _, interactions = _validated_spec(oracle_spec)

    missing = sorted(set(Q_COLUMNS) - set(fit_rows.columns))
    if missing:
        raise ValueError(f"FIT background is missing q columns: {missing}.")
    if fit_rows.empty:
        raise ValueError("FIT background must not be empty.")

    q = fit_rows.loc[:, Q_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(q).all():
        raise ValueError("FIT q-values contain non-finite values.")

    marginal = {
        criterion: float(q[:, index].mean())
        for index, criterion in enumerate(CRITERIA)
    }

    criterion_index = {criterion: index for index, criterion in enumerate(CRITERIA)}
    joint: dict[str, float] = {}
    for edge in interactions:
        left = str(edge.left)
        right = str(edge.right)
        left_values = q[:, criterion_index[left]]
        right_values = q[:, criterion_index[right]]
        joint[_pair_key(left, right)] = float(np.mean(left_values * right_values))

    return OracleBackgroundMoments(
        marginal_by_criterion=marginal,
        joint_by_pair=joint,
    )


def closed_form_oracle_shapley(
    evaluation_rows: pd.DataFrame,
    *,
    oracle_spec: Any,
    lambda_value: float,
    background_moments: OracleBackgroundMoments,
) -> np.ndarray:
    """Return local closed-form oracle Shapley values in C1..C10 order."""
    alpha, interactions = _validated_spec(oracle_spec)
    lam = _validated_lambda(lambda_value)

    missing = sorted(set(Q_COLUMNS) - set(evaluation_rows.columns))
    if missing:
        raise ValueError(f"Oracle evaluation rows are missing q columns: {missing}.")
    if evaluation_rows.empty:
        raise ValueError("Oracle evaluation rows must not be empty.")

    z = evaluation_rows.loc[:, Q_COLUMNS].to_numpy(dtype=float)
    if not np.isfinite(z).all():
        raise ValueError("Oracle evaluation q-values contain non-finite values.")
    if np.any(z < -NUMERICAL_TOL) or np.any(z > 1.0 + NUMERICAL_TOL):
        raise ValueError("Oracle evaluation q-values must lie in [0, 1].")

    if set(background_moments.marginal_by_criterion) != set(CRITERIA):
        raise ValueError("Background marginal moments must contain exactly C1..C10.")

    mu = np.asarray(
        [background_moments.marginal_by_criterion[c] for c in CRITERIA],
        dtype=float,
    )
    if not np.isfinite(mu).all():
        raise ValueError("Background marginal moments contain non-finite values.")

    expected_joint_keys = {_pair_key(edge.left, edge.right) for edge in interactions}
    if set(background_moments.joint_by_pair) != expected_joint_keys:
        raise ValueError("Background joint moments do not match the oracle interaction graph.")

    joint_values = np.asarray(
        list(background_moments.joint_by_pair.values()),
        dtype=float,
    )
    if not np.isfinite(joint_values).all():
        raise ValueError("Background joint moments contain non-finite values.")

    main_phi = alpha[None, :] * (z - mu[None, :])
    interaction_phi = np.zeros_like(main_phi)
    criterion_index = {criterion: index for index, criterion in enumerate(CRITERIA)}

    for edge in interactions:
        left = str(edge.left)
        right = str(edge.right)
        beta = float(edge.beta)
        j = criterion_index[left]
        k = criterion_index[right]

        z_j = z[:, j]
        z_k = z[:, k]
        mu_j = float(mu[j])
        mu_k = float(mu[k])
        mu_jk = float(background_moments.joint_by_pair[_pair_key(left, right)])

        interaction_phi[:, j] += 0.5 * beta * (
            z_j * mu_k - mu_jk
            + z_j * z_k - mu_j * z_k
        )
        interaction_phi[:, k] += 0.5 * beta * (
            mu_j * z_k - mu_jk
            + z_j * z_k - z_j * mu_k
        )

    phi = (main_phi + lam * interaction_phi) / (1.0 + lam)

    if phi.shape != (len(evaluation_rows), len(CRITERIA)):
        raise AssertionError("Unexpected oracle Shapley matrix shape.")
    if not np.isfinite(phi).all():
        raise ValueError("Closed-form oracle Shapley values are non-finite.")

    return phi


def compute_oracle_attribution_weights(
    oracle_rows: pd.DataFrame,
    *,
    replication_seed: int,
    n_contexts: int,
    oracle_spec: Any,
    lambda_value: float,
) -> OracleAttributionResult:
    """Compute frozen global oracle attribution-reference weights for one instance."""
    lam = _validated_lambda(lambda_value)
    _validated_spec(oracle_spec)

    fit, weight = prepare_oracle_attribution_rows(
        oracle_rows,
        replication_seed=replication_seed,
        n_contexts=n_contexts,
    )
    moments = compute_fit_background_moments(fit, oracle_spec=oracle_spec)
    phi = closed_form_oracle_shapley(
        weight,
        oracle_spec=oracle_spec,
        lambda_value=lam,
        background_moments=moments,
    )

    importance = np.mean(np.abs(phi), axis=0)
    if importance.shape != (len(FEATURES),):
        raise AssertionError("Unexpected oracle global-importance shape.")
    if not np.isfinite(importance).all() or np.any(importance < 0.0):
        raise ValueError("Oracle global importances are invalid.")

    total_importance = float(importance.sum())
    importance_by_feature = {
        feature: float(value)
        for feature, value in zip(FEATURES, importance, strict=True)
    }

    if total_importance <= IMPORTANCE_EPSILON:
        weights_defined = False
        weights_by_feature = None
    else:
        weights = importance / total_importance
        if not np.isfinite(weights).all() or np.any(weights < 0.0):
            raise ValueError("Normalized oracle attribution weights are invalid.")
        if not np.isclose(float(weights.sum()), 1.0, atol=NUMERICAL_TOL, rtol=0.0):
            raise ValueError("Normalized oracle attribution weights do not sum to one.")
        weights_defined = True
        weights_by_feature = {
            feature: float(value)
            for feature, value in zip(FEATURES, weights, strict=True)
        }

    diagnostics: dict[str, Any] = {
        "replication_seed": int(replication_seed),
        "N": int(n_contexts),
        "lambda": lam,
        "fit_background_rows": int(len(fit)),
        "weight_evaluation_rows": int(len(weight)),
        "background_partition": "fit",
        "evaluation_partition": "weight",
        "total_importance": total_importance,
        "importance_epsilon": IMPORTANCE_EPSILON,
        "undefined_oracle_attribution_weight_vector": not weights_defined,
        "equal_weight_fallback_used": False,
        "external_test_rows_used_for_background": 0,
        "external_test_rows_used_for_global_oracle_weights": 0,
        "target_Y_used": False,
        "predictive_model_fit": False,
        "shap_package_used": False,
        "mcdm_executed": False,
    }

    return OracleAttributionResult(
        replication_seed=int(replication_seed),
        n_contexts=int(n_contexts),
        lambda_value=lam,
        weights_defined=weights_defined,
        importance_by_feature=importance_by_feature,
        weights_by_feature=weights_by_feature,
        background_moments=moments,
        diagnostics=diagnostics,
    )
